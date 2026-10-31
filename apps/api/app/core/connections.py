import asyncio
import ipaddress
from urllib.parse import urlsplit
from fastapi import HTTPException


async def validate_service_url(value: str):
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(422, "Use an HTTPS workflow URL without embedded credentials.")
    if parsed.hostname in {"mcp.mekodata.ai", "api.mekodata.ai"}:
        raise HTTPException(422, "Meko access is managed by employee permissions, not a workflow connection.")
    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(parsed.hostname, parsed.port or 443)
    except OSError as exc:
        raise HTTPException(422, "The workflow service hostname could not be resolved.") from exc
    if any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise HTTPException(422, "Use a publicly reachable HTTPS workflow service.")
