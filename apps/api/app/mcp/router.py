from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import encrypt_token
from app.employees.models import Employee
from app.mcp.models import McpConnection
from app.mcp.schemas import (
    McpConnectionCreate,
    McpConnectionList,
    McpConnectionRead,
    McpConnectorRead,
)
from app.organizations.models import Organization
from app.agent.tools.executor import remote_tools
from app.employees.templates import get_template

router = APIRouter(prefix="/api/organizations/{org_id}", tags=["mcp"])

CONNECTOR_REGISTRY = [
    {
        "slug": "web_search",
        "name": "Exa Web Search",
        "description": "Search public web pages through Exa MCP. No key needed; service rate limits apply.",
        "auth_type": "none",
        "auth_types": ["none"],
        "requires_custom_server_url": False,
    },
    {
        "slug": "gmail",
        "name": "Gmail",
        "description": "Search and draft mail with Google Workspace.",
        "auth_type": "oauth2",
        "auth_types": ["oauth2"],
        "requires_custom_server_url": False,
    },
    {
        "slug": "gamma",
        "name": "Gamma",
        "description": "Generate decks and visual documents.",
        "auth_type": "oauth2",
        "auth_types": ["oauth2"],
        "requires_custom_server_url": False,
    },
    {
        "slug": "notion",
        "name": "Notion",
        "description": "Read and update Notion pages and databases.",
        "auth_type": "oauth2",
        "auth_types": ["oauth2", "pat_bearer"],
        "requires_custom_server_url": False,
    },
    {
        "slug": "vercel",
        "name": "Vercel",
        "description": "Inspect projects and deployments.",
        "auth_type": "oauth2",
        "auth_types": ["oauth2", "pat_bearer"],
        "requires_custom_server_url": False,
    },
    {
        "slug": "github",
        "name": "GitHub",
        "description": "Search repos, issues, and pull requests.",
        "auth_type": "oauth2",
        "auth_types": ["oauth2", "pat_bearer"],
        "requires_custom_server_url": False,
    },
    {
        "slug": "brave-search",
        "name": "Brave Search",
        "description": "Search the public web.",
        "auth_type": "api_key_header",
        "auth_types": ["api_key_header"],
        "requires_custom_server_url": False,
    },
    {
        "slug": "n8n",
        "name": "n8n",
        "description": "Connect to a self-hosted n8n MCP endpoint.",
        "auth_type": "pat_bearer",
        "auth_types": ["pat_bearer"],
        "requires_custom_server_url": True,
    },
    {
        "slug": "visualization",
        "name": "Visualization",
        "description": "Create downloadable SVG bar charts from supplied data.",
        "auth_type": "none",
        "auth_types": ["none"],
        "requires_custom_server_url": False,
    },
    {
        "slug": "canva",
        "name": "Canva",
        "description": "Generate and export designs.",
        "auth_type": "oauth2",
        "auth_types": ["oauth2"],
        "requires_custom_server_url": False,
    },
    {
        "slug": "pitchdeck",
        "name": "Pitch Deck Generator",
        "description": "Create editable PowerPoint files with speaker notes. No extra account needed.",
        "auth_type": "none",
        "auth_types": ["none"],
        "requires_custom_server_url": False,
    },
]


async def _access(db: AsyncSession, org_id: UUID, employee_id: UUID, user_id: UUID) -> None:
    org = await db.scalar(select(Organization).where(Organization.id == org_id, Organization.owner_id == user_id))
    employee = await db.scalar(select(Employee).where(Employee.id == employee_id, Employee.org_id == org_id))
    if org is None or employee is None:
        raise HTTPException(status_code=404, detail="Organization or employee not found")


@router.get("/mcp-connectors", response_model=list[McpConnectorRead])
async def list_connectors(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await db.scalar(
        select(Organization).where(
            Organization.id == org_id,
            Organization.owner_id == current_user.id,
        )
    )
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    connected = set(
        await db.scalars(
            select(McpConnection.connector_slug).where(
                McpConnection.org_id == org_id,
                McpConnection.status == "connected",
            )
        )
    )
    return [
        McpConnectorRead(
            **connector,
            is_connected=connector["slug"] in connected,
        )
        for connector in CONNECTOR_REGISTRY
    ]


@router.get("/employees/{employee_id}/mcp-connections", response_model=McpConnectionList)
async def list_connections(org_id: UUID, employee_id: UUID, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    await _access(db, org_id, employee_id, current_user.id)
    result = await db.scalars(select(McpConnection).where(McpConnection.org_id == org_id,
        (McpConnection.employee_id == employee_id) | (McpConnection.employee_id.is_(None)),
        McpConnection.status == "connected"))
    return McpConnectionList(connections=[McpConnectionRead.model_validate(item) for item in result])


@router.post("/employees/{employee_id}/mcp-connections/{connector_slug}", response_model=McpConnectionRead,
             status_code=status.HTTP_201_CREATED)
async def connect(org_id: UUID, employee_id: UUID, connector_slug: str, data: McpConnectionCreate,
                  db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _access(db, org_id, employee_id, current_user.id)
    native = connector_slug in {"pitchdeck", "visualization"}
    if connector_slug not in {"n8n", "web_search", "pitchdeck", "visualization"}:
        raise HTTPException(422, "This integration is not implemented yet.")
    employee = await db.get(Employee, employee_id)
    allowed = get_template(employee.employee_type or "general").allowed_mcp_servers
    if "*" not in allowed and connector_slug not in allowed:
        raise HTTPException(422, "This tool is not enabled for this employee role.")
    if connector_slug == "n8n" and (not data.server_url or not data.credential.strip()):
        raise HTTPException(422, "Provide the n8n HTTPS URL and access token.")
    try:
        if not native:
            await remote_tools(connector_slug, server_url=data.server_url, credential=data.credential)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, "Could not discover tools from this service. No connection was saved.") from exc
    employee_filter = McpConnection.employee_id.is_(None) if data.org_wide else (McpConnection.employee_id == employee_id)
    existing = await db.scalar(
        select(McpConnection).where(
            McpConnection.org_id == org_id,
            McpConnection.connector_slug == connector_slug,
            employee_filter,
            McpConnection.status == "connected",
        )
    )
    if existing is not None:
        return McpConnectionRead.model_validate(existing)
    connection = McpConnection(org_id=org_id, employee_id=None if data.org_wide else employee_id,
                               connector_slug=connector_slug,
                               auth_type="pat_bearer" if connector_slug == "n8n" else "none",
                               credentials_enc=encrypt_token(data.credential) if connector_slug == "n8n" else None,
                               server_url=data.server_url if connector_slug == "n8n" else None,
                               scopes=data.scopes, connected_by_user_id=current_user.id)
    db.add(connection)
    await db.commit()
    await db.refresh(connection)
    return McpConnectionRead.model_validate(connection)


@router.delete("/employees/{employee_id}/mcp-connections/{connector_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    org_id: UUID,
    employee_id: UUID,
    connector_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _access(db, org_id, employee_id, current_user.id)
    connection = await db.scalar(
        select(McpConnection).where(
            McpConnection.org_id == org_id,
            McpConnection.connector_slug == connector_slug,
            (
                (McpConnection.employee_id == employee_id)
                | (McpConnection.employee_id.is_(None))
            ),
        )
    )
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    await db.delete(connection)
    await db.commit()
