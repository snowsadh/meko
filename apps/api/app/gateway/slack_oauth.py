from uuid import UUID
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from slack_sdk.web.async_client import AsyncWebClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.oauth import decode_oauth_state, encode_oauth_state, frontend_redirect
from app.core.security import encrypt_token
from app.employees.models import Employee
from app.gateway.fixed_bots import get_fixed_bot
from app.memory.scopes import owned_employee, require_pack

router = APIRouter(prefix="/api/slack", tags=["slack"])
_SLACK_BOT_SCOPES = [
    "app_mentions:read",
    "channels:history",
    "groups:history",
    "chat:write",
    "im:history",
    "im:write",
    "mpim:history",
    "files:read",
    "files:write",
]


class InstallRequest(BaseModel):
    employee_id: UUID
    org_id: UUID


def redirect_uri(request):
    return (
        settings.slack_oauth_redirect_uri
        or str(request.base_url).rstrip("/") + "/api/slack/oauth/callback"
    )


def credentials(emp):
    if settings.slack_identity_mode == "fixed":
        bot = get_fixed_bot(emp.employee_type)
        if not bot or not bot.is_configured:
            raise HTTPException(503, "This employee's Slack app is not configured on the server.")
        return bot.client_id, bot.client_secret
    if not settings.slack_client_id or not settings.slack_client_secret:
        raise HTTPException(503, "Slack is not configured on the server.")
    return settings.slack_client_id, settings.slack_client_secret


@router.post("/install")
async def slack_install(
    data: InstallRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, emp = await owned_employee(db, data.org_id, data.employee_id, current_user.id)
    require_pack(org)
    require_pack(emp)
    client_id, _ = credentials(emp)
    # Only an authenticated owner can initiate linking. The previous GET accepted
    # arbitrary employee IDs and could bind another company's employee to a workspace.
    state = encode_oauth_state(
        "slack-oauth-state",
        employee_id=emp.id,
        org_id=org.id,
        extra_fields={"owner_id": str(current_user.id)},
        redirect_to=f"{settings.frontend_url.rstrip('/')}/dashboard/{emp.id}",
    )
    return {
        "authorize_url": "https://slack.com/oauth/v2/authorize?"
        + urlencode(
            {
                "client_id": client_id,
                "scope": ",".join(_SLACK_BOT_SCOPES),
                "state": state,
                "redirect_uri": redirect_uri(request),
            }
        )
    }


@router.get("/oauth/callback")
async def slack_oauth_callback(
    request: Request, code: str, state: str, db: AsyncSession = Depends(get_db)
):
    payload = decode_oauth_state(
        "slack-oauth-state", state, required_fields={"employee_id", "org_id", "owner_id"}
    )
    if payload is None:
        raise HTTPException(400, "Slack authorization expired. Start the connection again.")
    org, emp = await owned_employee(
        db, UUID(payload["org_id"]), UUID(payload["employee_id"]), UUID(payload["owner_id"])
    )
    client_id, secret = credentials(emp)
    response = await AsyncWebClient().oauth_v2_access(
        client_id=client_id, client_secret=secret, code=code, redirect_uri=redirect_uri(request)
    )
    if not response.get("ok") or not response.get("access_token"):
        raise HTTPException(502, "Slack did not authorize the employee.")
    team = response.get("team", {})
    if not team.get("id"):
        raise HTTPException(502, "Slack did not identify the workspace.")
    statement = select(Employee).where(Employee.slack_team_id == team["id"], Employee.id != emp.id)
    if settings.slack_identity_mode == "fixed":
        statement = statement.where(Employee.employee_type == emp.employee_type)
    if await db.scalar(statement):
        raise HTTPException(409, "This Slack app is already assigned in that workspace.")
    emp.slack_token_enc = encrypt_token(response["access_token"])
    emp.slack_team_id, emp.slack_team_name = team["id"], team.get("name")
    emp.slack_bot_user_id = response.get("bot_user_id")
    emp.status = "active"
    await db.commit()
    return frontend_redirect(
        str(emp.id),
        True,
        "slack",
        redirect_to=f"{settings.frontend_url.rstrip('/')}/dashboard/{emp.id}",
    )
