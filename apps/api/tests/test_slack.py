import asyncio
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from slack_sdk.socket_mode.request import SocketModeRequest

from app.agent import build
from app.agent.models import AgentRun
from app.core.config import settings
from app.core.meko import MekoError, meko
from app.core.security import decrypt_token, encrypt_token
from app.employees.models import Employee
from app.gateway import slack_oauth
from app.gateway import slack_bot
from app.gateway.models import SlackChunk, SlackMessage
from app.gateway.routing import (
    RouterChoice,
    RoutingDecision,
    SlackRouterWorker,
    choose_destinations,
    collect_chunk,
)
from app.gateway.slack_bot import SlackGateway
from app.organizations.models import Organization
from app.main import app
from tests.conftest import setup_company


class RouterModel:
    def __init__(self, company=False, employees=()):
        self.decision = RoutingDecision(
            company=company, employee_ids=list(employees), reason="Relevant work context."
        )
        self.calls = []

    def with_structured_output(self, *_args, **_kwargs):
        return self

    async def ainvoke(self, messages):
        self.calls.append(messages)
        roster = json.loads(messages[-1].content)["employees"]
        keys = {row["id"]: row["key"] for row in roster}
        return RouterChoice(
            company=self.decision.company,
            employee_keys=[
                keys.get(str(identifier), str(identifier))
                for identifier in self.decision.employee_ids
            ],
            reason=self.decision.reason,
        )


class SlackClient:
    posts = []
    fail = False

    def __init__(self, **_kwargs):
        pass

    async def chat_postMessage(self, **kwargs):  # noqa: N802 - Slack SDK method name
        self.posts.append(kwargs)
        if self.fail:
            raise TimeoutError("Uncertain delivery")
        return {"ok": True, "ts": f"170000001{len(self.posts)}.000001"}


async def connect(org, employee, *, team="TLOCAL", bot="USUPPORT"):
    async with build.async_session_factory() as db:
        company = await db.get(Organization, UUID(org["id"]))
        company.slack_team_id = team
        emp = await db.get(Employee, UUID(employee["id"]))
        emp.slack_team_id, emp.slack_bot_user_id = team, bot
        emp.slack_token_enc, emp.status = encrypt_token("synthetic-bot-token"), "active"
        await db.commit()


def event(
    text="A useful company update",
    *,
    ts="1700000000.000001",
    kind="message",
    channel="CLOCAL",
    **extra,
):
    return {
        "team_id": "TLOCAL",
        "event": {
            "type": kind,
            "channel": channel,
            "ts": ts,
            "text": text,
            "user": "UOPERATOR",
            "channel_type": "channel",
            **extra,
        },
    }


@pytest.mark.asyncio
async def test_oauth_ownership_state_and_workspace(product, monkeypatch):
    client, _, _ = product
    headers, org, support, _ = await setup_company(client)
    monkeypatch.setattr(
        slack_oauth, "credentials", lambda emp: ("synthetic-client", "synthetic-secret")
    )
    payload = {"org_id": org["id"], "employee_id": support["id"]}
    monkeypatch.setattr(settings, "slack_oauth_redirect_uri", "http://localhost/callback")
    assert (
        await client.post("/api/slack/install", headers=headers, json=payload)
    ).status_code == 503
    monkeypatch.setattr(
        settings, "slack_oauth_redirect_uri", "https://synthetic.example/api/slack/oauth/callback"
    )
    install = await client.post(
        "/api/slack/install",
        headers=headers,
        json={"org_id": org["id"], "employee_id": support["id"]},
    )
    assert install.status_code == 200
    query = parse_qs(urlparse(install.json()["authorize_url"]).query)
    state = query["state"][0]
    assert (
        await client.get(
            "/api/slack/oauth/callback", params={"state": state + "bad", "code": "test"}
        )
    ).status_code == 400
    denied = await client.get(
        "/api/slack/oauth/callback", params={"state": state, "error": "access_denied"}
    )
    assert denied.status_code == 303 and "slack=error" in denied.headers["location"]

    class OAuthClient:
        def __init__(self, **_kwargs):
            pass

        async def oauth_v2_access(self, **_kwargs):
            return {
                "ok": True,
                "access_token": "synthetic-bot-token",
                "bot_user_id": "USUPPORT",
                "team": {"id": "TLOCAL", "name": "Local tests"},
            }

    monkeypatch.setattr(slack_oauth, "AsyncWebClient", OAuthClient)
    linked = await client.get("/api/slack/oauth/callback", params={"state": state, "code": "test"})
    assert linked.status_code == 303 and "slack=connected" in linked.headers["location"]
    async with build.async_session_factory() as db:
        employee = await db.get(Employee, UUID(support["id"]))
        assert decrypt_token(employee.slack_token_enc) == "synthetic-bot-token"
        assert employee.slack_token_enc != "synthetic-bot-token"
        assert (await db.get(Organization, UUID(org["id"]))).slack_team_id == "TLOCAL"
    other_headers, other_org, other_support, _ = await setup_company(client, "other")
    assert (
        await client.post(
            "/api/slack/install",
            headers=other_headers,
            json={"org_id": org["id"], "employee_id": support["id"]},
        )
    ).status_code == 404
    other = await client.post(
        "/api/slack/install",
        headers=other_headers,
        json={"org_id": other_org["id"], "employee_id": other_support["id"]},
    )
    other_state = parse_qs(urlparse(other.json()["authorize_url"]).query)["state"][0]
    assert (
        await client.get("/api/slack/oauth/callback", params={"state": other_state, "code": "test"})
    ).status_code == 409


@pytest.mark.asyncio
async def test_listener_handles_installation_and_new_channels_without_restarting(product, monkeypatch):
    client, _, model = product
    headers, org, support, _ = await setup_company(client)
    opened = []

    class SocketClient:
        def __init__(self, **kwargs):
            self.socket_mode_request_listeners = []
            self.connected = False
            self.acks = []
            opened.append(self)

        async def connect(self):
            self.connected = True

        async def close(self):
            self.connected = False

        async def is_connected(self):
            return self.connected

        async def send_socket_mode_response(self, response):
            self.acks.append(response.envelope_id)

    class OAuthClient:
        def __init__(self, **kwargs):
            pass

        async def oauth_v2_access(self, **kwargs):
            return {"ok": True, "access_token": "synthetic-bot-token", "bot_user_id": "USUPPORT", "team": {"id": "TLOCAL", "name": "Local tests"}}

    monkeypatch.setattr(slack_bot, "SocketModeClient", SocketClient)
    monkeypatch.setattr(slack_bot, "FIXED_BOTS", {"support": SimpleNamespace(app_token="synthetic-app-token")})
    monkeypatch.setattr(slack_oauth, "AsyncWebClient", OAuthClient)
    monkeypatch.setattr(slack_oauth, "credentials", lambda emp: ("synthetic-client", "synthetic-secret"))
    monkeypatch.setattr(settings, "slack_oauth_redirect_uri", "https://synthetic.example/api/slack/oauth/callback")
    monkeypatch.setattr(settings, "slack_allowed_channel_ids", [])
    monkeypatch.setattr(settings, "slack_identity_mode", "fixed")
    monkeypatch.setattr(settings, "gateway_enabled", True)
    gateway = SlackGateway(build.async_session_factory, SlackClient)
    gateway.router.model = RouterModel()
    monkeypatch.setattr(app.state, "slack_gateway", gateway, raising=False)
    SlackClient.posts, SlackClient.fail = [], False
    await gateway.start()
    try:
        assert len(opened) == 1
        setup_url = f"/api/organizations/{org['id']}/slack/setup?employee_id={support['id']}"
        assert (await client.get(setup_url, headers=headers)).json()["listener_connected"] is False
        install = await client.post('/api/slack/install', headers=headers, json={'org_id': org['id'], 'employee_id': support['id']})
        state = parse_qs(urlparse(install.json()['authorize_url']).query)['state'][0]
        linked = await client.get('/api/slack/oauth/callback', params={'state': state, 'code': 'synthetic'})
        assert linked.status_code == 303
        assert (await client.get(setup_url, headers=headers)).json()["listener_connected"] is True

        socket = opened[0]
        listener = socket.socket_mode_request_listeners[0]
        for index, channel in enumerate(('CNEWONE', 'CNEWTWO')):
            request = SocketModeRequest(type='events_api', envelope_id=f'envelope-{index}', payload=event('<@USUPPORT> Help me', kind='app_mention', channel=channel))
            await listener(socket, request)
            assert request.envelope_id in socket.acks
        async with asyncio.timeout(15):
            while len(SlackClient.posts) < 2:
                await asyncio.sleep(0.05)
        assert len(opened) == 1  # One app connection covers both newly seen channels.
        assert {post['channel'] for post in SlackClient.posts} == {'CNEWONE', 'CNEWTWO'}
        assert len(model.messages) == 2
        assert all(post['text'] == 'A model stub reply for the request.' for post in SlackClient.posts)
        socket.connected = False
        assert (await client.get(setup_url, headers=headers)).json()["listener_connected"] is False
    finally:
        await gateway.stop()
    assert not await gateway.listener_connected('support')


@pytest.mark.asyncio
async def test_intake_dedup_thread_replies_and_uncertain_delivery(product):
    client, fake, model = product
    _, org, support, hr = await setup_company(client)
    await connect(org, support)
    await connect(org, hr, bot="UHR")
    SlackClient.posts, SlackClient.fail = [], False
    gateway = SlackGateway(build.async_session_factory, SlackClient)
    mention = event("<@USUPPORT> Help me", kind="app_mention")
    await gateway.process("support", mention)
    await gateway.process("support", mention)
    await gateway.process("support", event("<@USUPPORT> Help me"))
    await gateway.process("hr", event("<@USUPPORT> Help me"))
    await gateway.process("support", event("bot noise", ts="1700000001.000001", bot_id="BOTHER"))
    await gateway.process("support", {**event(), "team_id": "TOTHER"})
    async with build.async_session_factory() as db:
        runs = list((await db.scalars(select(AgentRun))).all())
        assert len(runs) == 1 and runs[0].status == "queued"
        identifier = runs[0].id
        assert len(list((await db.scalars(select(SlackMessage))).all())) == 1
    await gateway.reply(identifier)
    await gateway.reply(identifier)
    assert len(model.messages) == 1
    assert SlackClient.posts == [
        {
            "channel": "CLOCAL",
            "thread_ts": "1700000000.000001",
            "text": "A model stub reply for the request.",
        }
    ]
    async with build.async_session_factory() as db:
        run = await db.get(AgentRun, identifier)
        assert run.status == "completed" and run.delivery_status == "sent"
        assert run.capture_status == "router"
        assert len(list((await db.scalars(select(SlackMessage))).all())) == 2
    await build.capture_run(identifier)
    assert not fake.captures  # The shared router is the only automatic Slack writer.
    await gateway.process(
        "support", event("Follow up", ts="1700000003.000001", thread_ts="1700000000.000001")
    )
    async with build.async_session_factory() as db:
        followup = await db.scalar(select(AgentRun).where(AgentRun.input == "Follow up"))
        identifier = followup.id
    SlackClient.fail = True
    await gateway.reply(identifier)
    await gateway.reply(identifier)
    assert len(SlackClient.posts) == 2
    async with build.async_session_factory() as db:
        assert (await db.get(AgentRun, identifier)).delivery_status == "unconfirmed"
    SlackClient.fail = False


@pytest.mark.asyncio
async def test_channel_access_list_blocks_intake_and_queued_delivery(product, monkeypatch):
    client, _, model = product
    _, org, support, _ = await setup_company(client)
    await connect(org, support)
    SlackClient.posts, SlackClient.fail = [], False
    gateway = SlackGateway(build.async_session_factory, SlackClient)
    monkeypatch.setattr(settings, "slack_allowed_channel_ids", ["CTEST"])
    await gateway.process("support", event("<@USUPPORT> Outside", kind="app_mention"))
    async with build.async_session_factory() as db:
        assert not (await db.scalars(select(SlackMessage))).all()
        assert not (await db.scalars(select(AgentRun))).all()
    await gateway.process(
        "support", event("<@USUPPORT> Allowed", kind="app_mention", channel="CTEST")
    )
    async with build.async_session_factory() as db:
        run = await db.scalar(select(AgentRun))
        identifier = run.id
        assert (await db.scalar(select(SlackMessage))).channel_id == "CTEST"
    monkeypatch.setattr(settings, "slack_allowed_channel_ids", ["COTHER"])
    await gateway.reply(identifier)
    async with build.async_session_factory() as db:
        run = await db.get(AgentRun, identifier)
        assert run.status == "cancelled" and run.delivery_status == "not_sent"
    assert not model.messages and not SlackClient.posts


@pytest.mark.asyncio
async def test_paused_employee_and_private_roster(product):
    client, _, model = product
    headers, org, support, hr = await setup_company(client)
    await connect(org, support)
    await connect(org, hr, bot="UHR")
    SlackClient.posts, SlackClient.fail = [], False
    gateway = SlackGateway(build.async_session_factory, SlackClient)
    await gateway.process("support", event("Personal case", channel="DLOCAL", channel_type="im"))
    async with build.async_session_factory() as db:
        source = await db.scalar(select(SlackMessage))
        assert source.recipient_ids == [support["id"]]
        run = await db.scalar(select(AgentRun))
        identifier = run.id
        employee = await db.get(Employee, UUID(support["id"]))
        employee.status = "suspended"
        await db.commit()
    await gateway.reply(identifier)
    assert not model.messages and not SlackClient.posts
    async with build.async_session_factory() as db:
        assert (await db.get(AgentRun, identifier)).status == "cancelled"
    preview = await client.post(
        f"/api/organizations/{org['id']}/slack/routing/preview",
        headers=headers,
        json={"text": "A greeting", "employee_id": str(uuid4())},
    )
    assert preview.status_code == 404


@pytest.mark.asyncio
async def test_reply_worker_keeps_one_thread_in_order(product, monkeypatch):
    client, _, model = product
    _, org, support, _ = await setup_company(client)
    await connect(org, support)
    gateway = SlackGateway(build.async_session_factory, SlackClient)
    SlackClient.posts, SlackClient.fail = [], False
    await gateway.process("support", event("<@USUPPORT> First", kind="app_mention"))
    await gateway.process(
        "support", event("Second", ts="1700000001.000001", thread_ts="1700000000.000001")
    )
    started, release, entered = asyncio.Event(), asyncio.Event(), []
    original = model.ainvoke

    async def waiting_model(messages):
        entered.append(messages[-1].content)
        if len(entered) == 1:
            started.set()
            await release.wait()
        return await original(messages)

    monkeypatch.setattr(model, "ainvoke", waiting_model)
    worker = asyncio.create_task(gateway.run_replies())
    try:
        await asyncio.wait_for(started.wait(), timeout=5)
        await asyncio.sleep(1.2)  # Give the worker another poll while the first reply is blocked.
        assert entered == ["<@USUPPORT> First"]
        release.set()
        async with asyncio.timeout(6):
            while len(SlackClient.posts) != 2:
                await asyncio.sleep(0.05)
        assert entered == ["<@USUPPORT> First", "Second"]
    finally:
        release.set()
        gateway.stopping.set()
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)
        await gateway.stop()


@pytest.mark.asyncio
async def test_router_validates_private_scope_foreign_ids_and_disabled_memory(product):
    client, _, _ = product
    _, org, support, hr = await setup_company(client)
    async with build.async_session_factory() as db:
        company = await db.get(Organization, UUID(org["id"]))
        employees = list((await db.scalars(select(Employee))).all())
        messages = [
            {
                "channel_id": "DLOCAL",
                "ts": "1700.000001",
                "text": "Sensitive case",
                "user_id": "UOPERATOR",
                "recipient_ids": [support["id"]],
            }
        ]
        for chosen_company, identifiers, private in [
            (False, [uuid4()], False),
            (True, [], True),
            (False, [UUID(hr["id"])], True),
        ]:
            with pytest.raises(ValueError):
                await choose_destinations(
                    company,
                    employees,
                    messages,
                    private=private,
                    model=RouterModel(chosen_company, identifiers),
                )
        employee = await db.get(Employee, UUID(support["id"]))
        employee.auto_memory = False
        with pytest.raises(ValueError):
            await choose_destinations(
                company, employees, messages, model=RouterModel(False, [employee.id])
            )


@pytest.mark.asyncio
async def test_router_checkpoints_partial_delivery_and_manual_retry(product, monkeypatch):
    client, fake, _ = product
    headers, org, support, hr = await setup_company(client)
    await connect(org, support)
    gateway = SlackGateway(build.async_session_factory, SlackClient)
    await gateway.process(
        "support", event("The support duty owner is Maya. HR onboarding uses the Atlas handbook.")
    )
    monkeypatch.setattr(settings, "slack_router_batch_seconds", 0)
    monkeypatch.setattr(settings, "slack_memory_enabled", False)
    classifier = RouterModel(True, [UUID(support["id"]), UUID(hr["id"])])
    worker = SlackRouterWorker(build.async_session_factory, classifier)
    await worker.step()
    async with build.async_session_factory() as db:
        chunk = await db.scalar(select(SlackChunk))
        identifier = chunk.id
        assert chunk.status == "awaiting_memory"
    assert not fake.captures and not fake.files
    monkeypatch.setattr(settings, "slack_memory_enabled", True)
    original = fake.call

    async def fail_hr(name, *, datapack_id, **args):
        if name == "conversation_add_message" and datapack_id == hr["meko_datapack_id"]:
            raise MekoError("Synthetic HR service failure")
        return await original(name, datapack_id=datapack_id, **args)

    monkeypatch.setattr(meko, "call", fail_hr)
    await worker.step()
    async with build.async_session_factory() as db:
        chunk = await db.get(SlackChunk, identifier)
        assert chunk.status == "failed"
        assert chunk.deliveries["employee:" + support["id"]]["status"] == "saved"
        assert chunk.error == "Synthetic HR service failure"
    assert len(fake.captures) == 1
    assert not await worker.step()  # Failed chunks require a deliberate retry.
    monkeypatch.setattr(meko, "call", original)
    retried = await client.post(
        f"/api/organizations/{org['id']}/slack/routing/{identifier}/retry", headers=headers
    )
    assert retried.status_code == 200
    await worker.step()
    async with build.async_session_factory() as db:
        chunk = await db.get(SlackChunk, identifier)
        assert chunk.status == "complete"
        assert all(target["status"] == "saved" for target in chunk.deliveries.values())
    assert len(fake.captures) == 2 and len(classifier.calls) == 1
    writes = [call for call in fake.calls if call[0] == "conversation_add_message"]
    assert len(writes) == 2
    response = await client.get(
        f"/api/organizations/{org['id']}/slack/routing?employee_id={support['id']}", headers=headers
    )
    assert response.status_code == 200 and len(response.json()) == 1


@pytest.mark.asyncio
async def test_chunk_boundaries_noop_and_context_change(product, monkeypatch):
    client, fake, _ = product
    _, org, support, _ = await setup_company(client)
    await connect(org, support)
    gateway = SlackGateway(build.async_session_factory, SlackClient)
    await gateway.process("support", event("hi"))
    await gateway.process(
        "support", event("Other channel", ts="1700000001.000001", channel="COTHER")
    )
    await gateway.process(
        "support", event("Thread", ts="1700000002.000001", thread_ts="1700000000.000001")
    )
    monkeypatch.setattr(settings, "slack_router_batch_seconds", 30)
    async with build.async_session_factory() as db:
        assert await collect_chunk(db) is None
        for _ in range(3):
            chunk = await collect_chunk(db, now=datetime.now(UTC) + timedelta(minutes=1))
            assert len(chunk.messages) == 1
        assert await collect_chunk(db, now=datetime.now(UTC) + timedelta(minutes=1)) is None
    classifier = RouterModel()
    worker = SlackRouterWorker(build.async_session_factory, classifier)
    monkeypatch.setattr(settings, "slack_memory_enabled", False)
    await worker.step()
    async with build.async_session_factory() as db:
        assert (
            await db.scalar(select(SlackChunk).where(SlackChunk.status == "complete"))
        ).employee_ids == []
    classifier.decision.employee_ids = [UUID(support["id"])]
    await worker.step()
    async with build.async_session_factory() as db:
        employee = await db.get(Employee, UUID(support["id"]))
        employee.context_version += 1
        await db.commit()
    monkeypatch.setattr(settings, "slack_memory_enabled", True)
    await worker.step()  # The other pending chunk uses the current version.
    await worker.step()  # The older decision is skipped after its context changed.
    async with build.async_session_factory() as db:
        chunks = list((await db.scalars(select(SlackChunk))).all())
        statuses = [target["status"] for chunk in chunks for target in chunk.deliveries.values()]
        assert sorted(statuses) == ["saved", "skipped"]
    assert len(fake.captures) == 1


@pytest.mark.asyncio
async def test_indexing_checks_are_spaced_and_service_errors_stop_retrying(product, monkeypatch):
    client, fake, _ = product
    _, org, support, _ = await setup_company(client)
    await connect(org, support)
    gateway = SlackGateway(build.async_session_factory, SlackClient)
    await gateway.process("support", event("Approved company policy: all staff must use 2FA."))
    monkeypatch.setattr(settings, "slack_router_batch_seconds", 0)
    monkeypatch.setattr(settings, "slack_memory_enabled", True)
    worker = SlackRouterWorker(build.async_session_factory, RouterModel(True))
    await worker.step()
    assert len(fake.files[org["meko_datapack_id"]]) == 1
    assert not await worker.step()  # No rapid polling while indexing is pending.
    async with build.async_session_factory() as db:
        chunk = await db.scalar(select(SlackChunk))
        identifier = chunk.id
        chunk.claimed_at = datetime.now(UTC) - timedelta(seconds=31)
        await db.commit()

    async def unavailable(*_args, **_kwargs):
        raise MekoError("Synthetic quota error")

    monkeypatch.setattr(meko, "document_status", unavailable)
    await worker.step()
    async with build.async_session_factory() as db:
        chunk = await db.get(SlackChunk, identifier)
        assert chunk.status == "failed" and chunk.error == "Synthetic quota error"
    assert not await worker.step()  # No automatic calls after a provider error.
