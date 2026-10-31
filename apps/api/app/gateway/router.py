from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select

from app.auth.models import User
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.employees.models import Employee
from app.gateway.fixed_bots import get_fixed_bot
from app.gateway.models import SlackChunk
from app.gateway.routing import RoutingDecision, choose_destinations
from app.gateway.slack_oauth import _SLACK_BOT_SCOPES
from app.memory.scopes import owned_employee, owned_org
from app.memory_sources.service import get_source_model, retry_source

router = APIRouter(prefix="/api/organizations/{org_id}/slack", tags=["slack-routing"])


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    channel_id: str
    thread_ts: str | None
    private: bool
    messages: list[dict]
    status: str
    company: bool
    employee_ids: list[str]
    reason: str | None
    deliveries: dict
    error: str | None
    created_at: datetime


class PreviewRequest(BaseModel):
    text: str = Field(min_length=1, max_length=16000)
    employee_id: UUID | None = None
    private: bool = False


@router.post("/routing/preview", response_model=RoutingDecision)
async def preview(
    org_id: UUID, data: PreviewRequest, db=Depends(get_db), user: User = Depends(get_current_user)
):
    org = await owned_org(db, org_id, user.id)
    if data.employee_id:
        await owned_employee(db, org_id, data.employee_id, user.id)
    employees = list((await db.scalars(select(Employee).where(Employee.org_id == org.id))).all())
    message = {
        "channel_id": "preview",
        "ts": "preview",
        "user_id": "operator",
        "text": data.text,
        "recipient_ids": [str(data.employee_id)] if data.employee_id else [],
        "is_bot": False,
    }
    try:
        return await choose_destinations(org, employees, [message], private=data.private)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/routing", response_model=list[ChunkResponse])
async def chunks(
    org_id: UUID,
    employee_id: UUID | None = None,
    limit: int = Query(20, ge=1, le=50),
    db=Depends(get_db),
    user: User = Depends(get_current_user),
):
    await owned_org(db, org_id, user.id)
    statement = select(SlackChunk).where(SlackChunk.org_id == org_id)
    if employee_id:
        await owned_employee(db, org_id, employee_id, user.id)
        statement = statement.where(
            or_(
                SlackChunk.company.is_(True),
                SlackChunk.employee_ids.contains([str(employee_id)]),
                SlackChunk.messages.contains([{"recipient_ids": [str(employee_id)]}]),
            )
        )
    return list(
        (await db.scalars(statement.order_by(SlackChunk.created_at.desc()).limit(limit))).all()
    )


@router.post("/routing/{chunk_id}/retry", response_model=ChunkResponse)
async def retry(
    org_id: UUID, chunk_id: UUID, db=Depends(get_db), user: User = Depends(get_current_user)
):
    await owned_org(db, org_id, user.id)
    chunk = await db.scalar(
        select(SlackChunk).where(SlackChunk.org_id == org_id, SlackChunk.id == chunk_id)
    )
    if chunk is None:
        raise HTTPException(404, "Routing chunk not found")
    if chunk.status not in {"failed", "awaiting_memory"}:
        raise HTTPException(409, "Only failed or waiting chunks can be retried.")
    target = chunk.deliveries.get("company", {})
    if target.get("status") == "failed" and target.get("source_id"):
        source = await get_source_model(db, org_id, UUID(target["source_id"]), user.id)
        if source and source.status == "failed":
            await retry_source(db, org_id, source.id, user.id)
    chunk.status, chunk.error, chunk.claimed_at = "pending", None, None
    await db.commit()
    return chunk


@router.get("/setup")
async def setup(
    org_id: UUID,
    request: Request,
    employee_id: UUID,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
):
    org, employee = await owned_employee(db, org_id, employee_id, user.id)
    app = get_fixed_bot(employee.employee_type)
    configured = bool(app and app.is_configured)
    if settings.slack_identity_mode == "shared":
        configured = bool(
            settings.slack_client_id and settings.slack_client_secret and settings.slack_app_token
        )
    return {
        "app_configured": configured,
        "gateway_enabled": settings.gateway_enabled,
        "memory_delivery_enabled": settings.slack_memory_enabled,
        "workspace": org.slack_team_name,
        "connected": bool(employee.slack_token_enc),
        "oauth_redirect_uri": settings.slack_oauth_redirect_uri
        or str(request.base_url).rstrip("/") + "/api/slack/oauth/callback",
        "required_scopes": _SLACK_BOT_SCOPES,
        "required_events": [
            "app_mention",
            "message.channels",
            "message.groups",
            "message.im",
            "message.mpim",
        ],
        "socket_mode_required": True,
    }
