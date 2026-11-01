"""Durable Socket Mode intake, employee replies, and one company memory router."""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web.async_client import AsyncWebClient
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import aliased

from app.agent.build import run_agent
from app.agent.models import AgentRun
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import decrypt_token
from app.employees.models import Employee
from app.gateway.fixed_bots import FIXED_BOTS
from app.gateway.models import SlackMessage
from app.gateway.routing import SlackRouterWorker
from app.organizations.models import Organization

logger = logging.getLogger(__name__)


async def record_message(db, org_id, employee_id, event, *, is_bot=False):
    """Message identity is shared across app_mention/message events and role apps."""
    channel_type = event.get("channel_type", "channel")
    recipients = [str(employee_id)] if channel_type in {"im", "mpim"} else []
    values = dict(
        id=uuid4(),
        org_id=org_id,
        channel_id=event["channel"],
        message_ts=event["ts"],
        thread_ts=event.get("thread_ts"),
        channel_type=channel_type,
        user_id=event.get("user", "unknown"),
        text=event["text"],
        is_bot=is_bot,
        recipient_ids=recipients,
    )
    identifier = await db.scalar(
        insert(SlackMessage)
        .values(**values)
        .on_conflict_do_nothing(constraint="uq_slack_source_message")
        .returning(SlackMessage.id)
    )
    if identifier is None and recipients:
        row = await db.scalar(
            select(SlackMessage)
            .where(
                SlackMessage.org_id == org_id,
                SlackMessage.channel_id == event["channel"],
                SlackMessage.message_ts == event["ts"],
            )
            .with_for_update()
        )
        row.recipient_ids = sorted(set(row.recipient_ids + recipients))
    return identifier


class SlackGateway:
    def __init__(self, session_factory=async_session_factory, web_client=AsyncWebClient):
        self.session_factory, self.web_client = session_factory, web_client
        self.clients, self.workers = {}, []
        self.pending = {}
        self.stopping = asyncio.Event()
        self.router = SlackRouterWorker(session_factory)

    async def start(self):
        # ponytail: one gateway process; add distributed leases if replicas become necessary.
        async with self.session_factory() as db:
            await db.execute(
                update(AgentRun)
                .where(AgentRun.platform == "slack", AgentRun.status == "running")
                .values(
                    status="failed",
                    delivery_status="not_sent",
                    capture_status="router",
                    error="Work interrupted. Inspect tool results before starting it again.",
                )
            )
            await db.execute(
                update(AgentRun)
                .where(AgentRun.platform == "slack", AgentRun.delivery_status == "posting")
                .values(
                    delivery_status="unconfirmed",
                    error="Delivery was interrupted. Check the Slack thread before retrying.",
                )
            )
            await db.commit()
        apps = {role: bot.app_token for role, bot in FIXED_BOTS.items() if bot.app_token}
        if settings.slack_identity_mode == "shared":
            apps = {"shared": settings.slack_app_token} if settings.slack_app_token else {}
        for role, token in apps.items():
            client = SocketModeClient(app_token=token, web_client=AsyncWebClient())

            async def listener(socket, request, employee_type=role):
                if request.type == "events_api":
                    try:
                        async with asyncio.timeout(2.5):
                            await self.process(employee_type, request.payload)
                    except Exception:
                        # No acknowledgement: Slack can retry an intake that did not finish.
                        logger.error(
                            "Slack intake was not confirmed for %s; waiting for retry",
                            employee_type,
                        )
                        return
                await socket.send_socket_mode_response(
                    SocketModeResponse(envelope_id=request.envelope_id)
                )

            client.socket_mode_request_listeners.append(listener)
            try:
                await client.connect()
                self.clients[role] = client
            except Exception:
                await client.close()
                logger.error("Could not connect the Slack app for %s", role)
        self.workers = [
            asyncio.create_task(self.run_replies()),
            asyncio.create_task(self.router.run()),
        ]

    async def stop(self):
        self.stopping.set()
        self.router.stopping.set()
        for client in self.clients.values():
            await client.close()
        self.clients.clear()
        for task in self.workers:
            task.cancel()
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        if self.pending:
            tasks = list(self.pending.values())
            try:
                await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=5)
            except TimeoutError:
                pass

    async def listener_connected(self, employee_type):
        role = "shared" if settings.slack_identity_mode == "shared" else employee_type
        client = self.clients.get(role)
        return client is not None and await client.is_connected()

    async def process(self, role, payload):
        event = payload.get("event", {})
        if (
            event.get("type") not in {"message", "app_mention"}
            or event.get("bot_id")
            or event.get("subtype")
        ):
            return
        if not all(
            isinstance(event.get(key), str) and event[key]
            for key in ("channel", "ts", "text", "user")
        ):
            return
        if not event["text"].strip() or len(event["text"]) > 40000:
            return
        if settings.slack_allowed_channel_ids and event["channel"] not in settings.slack_allowed_channel_ids:
            return
        async with self.session_factory() as db:
            statement = select(Employee).where(
                Employee.slack_team_id == payload.get("team_id"),
                Employee.status == "active",
                Employee.slack_token_enc.is_not(None),
            )
            if role != "shared":
                statement = statement.where(Employee.employee_type == role)
            employees = list((await db.scalars(statement)).all())
            if len(employees) != 1:
                return
            employee = employees[0]
            org = await db.get(Organization, employee.org_id)
            if org is None or org.slack_team_id != payload.get("team_id"):
                return
            # Socket Mode delivers channel history only for channels this installed bot can see.
            await record_message(db, org.id, employee.id, event)
            direct = event.get("channel_type") in {"im", "mpim"}
            mention = event["type"] == "app_mention" and (
                not employee.slack_bot_user_id
                or f"<@{employee.slack_bot_user_id}>" in event["text"]
            )
            root_ts = event.get("thread_ts") or event["ts"]
            thread_key = f"slack:{event['channel']}:{root_ts}"
            participating = False
            if event.get("thread_ts") and not (direct or mention):
                participating = bool(
                    await db.scalar(
                        select(AgentRun.id)
                        .where(
                            AgentRun.employee_id == employee.id,
                            AgentRun.thread_key == thread_key,
                            AgentRun.status.in_(["queued", "running", "completed"]),
                        )
                        .limit(1)
                    )
                )
            if direct or mention or participating:
                key = f"{employee.id}:slack:{event['channel']}:{event['ts']}"
                await db.execute(
                    insert(AgentRun)
                    .values(
                        id=uuid4(),
                        org_id=org.id,
                        employee_id=employee.id,
                        request_key=key,
                        thread_key=thread_key,
                        platform="slack",
                        input=event["text"],
                        recalled=[],
                        tools=[],
                        status="queued",
                        capture_status="router",
                        delivery_status="pending",
                        context_version=employee.context_version,
                        slack_channel_id=event["channel"],
                        slack_thread_ts=root_ts,
                    )
                    .on_conflict_do_nothing(index_elements=[AgentRun.request_key])
                )
            await db.commit()

    async def reply(self, run_id):
        async with self.session_factory() as db:
            run = await db.get(AgentRun, run_id)
            if run is None:
                return
            if settings.slack_allowed_channel_ids and run.slack_channel_id not in settings.slack_allowed_channel_ids:
                run.status, run.delivery_status = "cancelled", "not_sent"
                run.error = "This channel is outside the configured Slack access list."
                await db.commit()
                return
            employee = await db.get(Employee, run.employee_id)
            if not employee or employee.status != "active" or not employee.slack_token_enc:
                run.status, run.delivery_status = "cancelled", "not_sent"
                run.error = "Employee paused or disconnected before this reply was sent."
                await db.commit()
                return
            org = await db.get(Organization, run.org_id)
            try:
                if run.status == "queued":
                    run = await run_agent(
                        db,
                        org_id=org.id,
                        employee_id=employee.id,
                        user_id=org.owner_id,
                        message=run.input,
                        platform="slack",
                        thread_key=run.thread_key,
                        request_key=run.request_key.removeprefix(str(employee.id) + ":"),
                    )
                if run.status != "completed" or run.delivery_status != "pending":
                    return
                # Recheck a pause/disconnect that occurred while the model was working.
                await db.refresh(employee)
                if employee.status != "active" or not employee.slack_token_enc:
                    run.delivery_status = "not_sent"
                    run.error = "Employee paused or disconnected before delivery."
                    await db.commit()
                    return
                claimed = await db.scalar(
                    update(AgentRun)
                    .where(AgentRun.id == run.id, AgentRun.delivery_status == "pending")
                    .values(delivery_status="posting")
                    .returning(AgentRun.id)
                )
                await db.commit()
                if claimed is None:
                    return
                text = (run.output or "I couldn't complete that request.")[:35000]
                # Disable SDK retries: a timeout can follow a successful chat.postMessage.
                client = self.web_client(
                    token=decrypt_token(employee.slack_token_enc), timeout=30, retry_handlers=[]
                )
                try:
                    response = await client.chat_postMessage(
                        channel=run.slack_channel_id, thread_ts=run.slack_thread_ts, text=text
                    )
                    if not response.get("ok") or not response.get("ts"):
                        raise ValueError("Slack did not confirm a message identifier.")
                except Exception:
                    run.delivery_status = "unconfirmed"
                    run.error = (
                        "Slack delivery was not confirmed. Check the thread before retrying."
                    )
                    await db.commit()
                    return
                source = await db.scalar(
                    select(SlackMessage)
                    .where(
                        SlackMessage.org_id == org.id,
                        SlackMessage.channel_id == run.slack_channel_id,
                    )
                    .limit(1)
                )
                await record_message(
                    db,
                    org.id,
                    employee.id,
                    {
                        "channel": run.slack_channel_id,
                        "ts": response["ts"],
                        "thread_ts": run.slack_thread_ts,
                        "channel_type": source.channel_type if source else "channel",
                        "user": employee.slack_bot_user_id or "AI employee",
                        "text": text,
                    },
                    is_bot=True,
                )
                run.delivery_status = "sent"
                await db.commit()
            except Exception:
                await db.rollback()
                logger.error("Employee reply failed; inspect its activity record")

    async def run_replies(self):
        while not self.stopping.is_set():
            try:
                async with self.session_factory() as db:
                    earlier = aliased(AgentRun)
                    unfinished = (
                        select(earlier.id)
                        .where(
                            earlier.employee_id == AgentRun.employee_id,
                            earlier.thread_key == AgentRun.thread_key,
                            earlier.created_at < AgentRun.created_at,
                            (earlier.status.in_(["queued", "running"]))
                            | (
                                (earlier.status == "completed")
                                & earlier.delivery_status.in_(["pending", "posting"])
                            ),
                        )
                        .exists()
                    )
                    due = list(
                        (
                            await db.scalars(
                                select(AgentRun.id)
                                .where(
                                    AgentRun.platform == "slack",
                                    ~unfinished,
                                    (AgentRun.status == "queued")
                                    | (
                                        (AgentRun.status == "completed")
                                        & (AgentRun.delivery_status == "pending")
                                    ),
                                )
                                .order_by(AgentRun.created_at)
                                .limit(
                                    max(0, settings.agent_worker_concurrency - len(self.pending))
                                )
                            )
                        ).all()
                    )
                for identifier in due:
                    if identifier in self.pending:
                        continue
                    task = asyncio.create_task(self.reply(identifier))
                    self.pending[identifier] = task
                    task.add_done_callback(lambda _, key=identifier: self.pending.pop(key, None))
            except Exception:
                logger.error("Slack reply worker failed; its durable queue is retained")
            try:
                await asyncio.wait_for(self.stopping.wait(), timeout=1)
            except TimeoutError:
                pass
