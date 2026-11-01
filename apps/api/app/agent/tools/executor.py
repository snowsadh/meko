from __future__ import annotations

import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient
from sqlalchemy import select

from app.core.connections import validate_service_url
from app.core.security import decrypt_token
from app.employees.templates import get_template

EXA_URL = "https://mcp.exa.ai/mcp?tools=web_search_exa"


async def remote_tools(slug, *, server_url=None, credential=""):
    """Discover real tools; never accept a connection based only on a saved token."""
    if slug == "web_search":
        url, headers = EXA_URL, {}
    elif slug == "n8n" and server_url and credential:
        url, headers = server_url, {"Authorization": f"Bearer {credential}"}
    else:
        raise ValueError("This service is not supported or its credentials are missing.")
    await validate_service_url(url)
    client = MultiServerMCPClient(
        {slug: {"url": url, "transport": "streamable_http", "headers": headers}},
        tool_name_prefix=True,
    )
    tools = await asyncio.wait_for(client.get_tools(), timeout=25)
    if not tools:
        raise ValueError("The service did not expose any tools.")
    return tools


async def connected_tools(db, employee, run=None):
    from app.mcp.models import McpConnection

    connections = list(
        (
            await db.scalars(
                select(McpConnection).where(
                    McpConnection.org_id == employee.org_id,
                    McpConnection.status == "connected",
                    (McpConnection.employee_id == employee.id)
                    | McpConnection.employee_id.is_(None),
                )
            )
        ).all()
    )
    allowed = get_template(employee.employee_type or "general").allowed_mcp_servers
    tools, seen = [], set()
    for connection in connections:
        slug = connection.connector_slug
        if slug in seen or ("*" not in allowed and slug not in allowed):
            continue
        seen.add(slug)
        try:
            if slug in {"pitchdeck", "visualization"} and run is not None:
                from app.agent.tools.files import file_tools

                tools.extend(file_tools(db, employee, run, slug))
                continue
            if slug not in {"web_search", "n8n"}:
                continue
            tools.extend(
                await remote_tools(
                    slug,
                    server_url=connection.server_url,
                    credential=decrypt_token(connection.credentials_enc)
                    if connection.credentials_enc
                    else "",
                )
            )
        except Exception:
            # One unavailable service must not disable normal chat or other tools.
            if run is not None:
                run.tools = [
                    *run.tools,
                    {
                        "name": f"{slug}_connection",
                        "arguments": {},
                        "status": "failed",
                        "result": (
                            "Tool discovery failed. This service was unavailable for this request."
                        ),
                    },
                ]
    return tools
