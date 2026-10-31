"""One Socket Mode connection per configured Slack app; route by workspace and role."""

from __future__ import annotations

import asyncio
import logging

from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web.async_client import AsyncWebClient
from sqlalchemy import select

from app.agent.build import run_agent, capture_run
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import decrypt_token
from app.employees.models import Employee
from app.gateway.fixed_bots import FIXED_BOTS
from app.organizations.models import Organization

logger = logging.getLogger(__name__)


class SlackGateway:
    def __init__(self):
        self.clients = []
        self.pending = set()

    async def start(self):
        apps = {kind: bot.app_token for kind, bot in FIXED_BOTS.items() if bot.app_token}
        if settings.slack_identity_mode == "shared":
            apps = {"shared": settings.slack_app_token} if settings.slack_app_token else {}
        for role, token in apps.items():
            client = SocketModeClient(app_token=token, web_client=AsyncWebClient())

            async def listener(socket, request, employee_type=role):
                if request.type != "events_api":
                    return
                await socket.send_socket_mode_response(
                    SocketModeResponse(envelope_id=request.envelope_id)
                )
                task = asyncio.create_task(self.process(employee_type, request.payload))
                self.pending.add(task)
                task.add_done_callback(self.pending.discard)

            client.socket_mode_request_listeners.append(listener)
            try:
                await client.connect()
                self.clients.append(client)
            except Exception:
                await client.close()
                logger.error("Could not connect the Slack app for %s", role)

    async def stop(self):
        for client in self.clients:
            await client.close()
        if self.pending:
            await asyncio.gather(*self.pending, return_exceptions=True)

    async def process(self, role, payload):
        event = payload.get("event", {})
        if event.get("bot_id") or event.get("subtype") or not event.get("text", "").strip():
            return
        direct = event.get("type") == "message" and event.get("channel_type") == "im"
        mention = event.get("type") == "app_mention"
        # Channel replies are accepted only inside a thread this employee already joined.
        thread_reply = event.get("type") == "message" and event.get("thread_ts")
        if not (direct or mention or thread_reply):
            return
        async with async_session_factory() as db:
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
            emp = employees[0]
            org = await db.get(Organization, emp.org_id)
            root_ts = event.get("thread_ts") or event.get("ts")
            thread_key = f"slack:{event['channel']}:{root_ts}"
            if thread_reply and not (direct or mention):
                from app.agent.models import AgentRun

                participation = await db.scalar(
                    select(AgentRun.id)
                    .where(AgentRun.employee_id == emp.id, AgentRun.thread_key == thread_key)
                    .limit(1)
                )
                if not participation:
                    return
            event_id = payload.get("event_id")
            if not event_id or not org:
                return
            try:
                run = await run_agent(
                    db,
                    org_id=org.id,
                    employee_id=emp.id,
                    user_id=org.owner_id,
                    message=event["text"],
                    platform="slack",
                    thread_key=thread_key,
                    request_key=f"slack:{event_id}",
                )
                if not getattr(run, "_new_request", False):
                    return
                token = decrypt_token(emp.slack_token_enc)
                client = AsyncWebClient(token=token)
                # No automatic resend on an uncertain delivery: a timeout can follow a successful post.
                try:
                    await client.chat_postMessage(
                        channel=event["channel"],
                        thread_ts=root_ts,
                        text=(run.output or "I couldn't complete that request.")[:35000],
                    )
                except Exception:
                    run.delivery_status = "unconfirmed"
                    run.error = (
                        "Slack delivery was not confirmed. Check the thread before retrying."
                    )
                    await db.commit()
                    return
                run.delivery_status = "sent"
                await db.commit()
                if run.capture_status == "pending":
                    await capture_run(run.id)
            except Exception:
                await db.rollback()
                logger.error("Slack request failed for employee %s; inspect its activity", emp.id)
