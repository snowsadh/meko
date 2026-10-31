from __future__ import annotations

from langchain_mcp_adapters.client import MultiServerMCPClient
from sqlalchemy import select

from app.core.security import decrypt_token
from app.mcp.models import McpConnection


async def connected_tools(db, employee):
    connections = list((await db.scalars(select(McpConnection).where(
        McpConnection.org_id == employee.org_id, McpConnection.status == "connected",
        (McpConnection.employee_id == employee.id) | McpConnection.employee_id.is_(None),
        McpConnection.connector_slug == "n8n"))).all())
    if not connections:
        return []
    from app.core.connections import validate_service_url
    servers = {}
    for connection in connections:
        if not connection.server_url or not connection.server_url.startswith("https://"):
            raise ValueError("Connected MCP services must use HTTPS.")
        await validate_service_url(connection.server_url)
        servers[f"n8n_{connection.id.hex[:8]}"] = {
            "url": connection.server_url, "transport": "streamable_http",
            "headers": {"Authorization": f"Bearer {decrypt_token(connection.credentials_enc)}"},
        }
    return await MultiServerMCPClient(servers, tool_name_prefix=True).get_tools()
