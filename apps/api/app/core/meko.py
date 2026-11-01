"""Meko's documented MCP tools and public HTTP file API; no local memory fallback."""

from __future__ import annotations

import json
import base64
import hashlib
import asyncio
import logging
import time
from typing import Any
from uuid import UUID

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.core.config import settings

BUILD_DATAPACK_ID = "e6b3af37-3006-4337-bfd1-51c7e50b2207"
DEFAULT_DATAPACK_ID = "71dadccc-232c-4d99-b53a-e4e7fa6abf54"
logger = logging.getLogger(__name__)


class MekoError(RuntimeError):
    pass


def product_pack(value: str) -> str:
    value = str(UUID(str(value)))
    if value == BUILD_DATAPACK_ID:
        raise MekoError("The coding team's build datapack cannot be used by the product.")
    if value == DEFAULT_DATAPACK_ID:
        raise MekoError("The default datapack is not authorized for product access.")
    return value


def decode_result(result: Any) -> Any:
    """Unwrap MCP's JSON-in-text result, including errors inside a successful transport."""
    if getattr(result, "isError", False):
        raise MekoError("Meko rejected the operation.")
    value = getattr(result, "structuredContent", None)
    if value is None:
        texts = [block.text for block in result.content if getattr(block, "type", "") == "text"]
        if len(texts) != 1:
            raise MekoError("Meko returned an unexpected response.")
        value = texts[0]
    for _ in range(4):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError as exc:
                raise MekoError("Meko returned a non-JSON response.") from exc
        elif isinstance(value, dict) and set(value) == {"result"}:
            value = value["result"]
        else:
            break
    if isinstance(value, dict):
        error = value.get("error")
        detail = value.get("detail")
        if error or value.get("status") == "error" or (detail and len(value) == 1):
            message = error or detail or "Meko rejected the operation."
            if isinstance(message, dict):
                message = message.get("message", "Meko rejected the operation.")
            raise MekoError(str(message)[:400])
    if not isinstance(value, (dict, list)):
        raise MekoError("Meko returned an unexpected response.")
    return value


class MekoClient:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None):
        self.transport = transport

    @property
    def headers(self) -> dict[str, str]:
        if not settings.meko_product_api_key:
            raise MekoError("Set MEKO_PRODUCT_API_KEY on the server to connect company memory.")
        return {
            "Authorization": f"Bearer {settings.meko_product_api_key}",
            "User-Agent": "openhuman/0.1",
        }

    async def http(self, method: str, path: str, **kwargs: Any) -> Any:
        async with httpx.AsyncClient(
            base_url=settings.meko_api_url.rstrip("/"),
            headers=self.headers,
            timeout=settings.meko_timeout_seconds,
            transport=self.transport,
        ) as client:
            try:
                response = await client.request(method, path, **kwargs)
                body = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise MekoError("Could not reach Meko. The operation is not confirmed.") from exc
        if not response.is_success or body.get("error"):
            error = body.get("error") or body.get("detail") or "Meko rejected the operation."
            if isinstance(error, dict):
                error = error.get("message", "Meko rejected the operation.")
            raise MekoError(str(error)[:400])
        if "data" not in body:
            raise MekoError("Meko returned an unexpected HTTP response.")
        return body["data"]

    async def call(self, name: str, *, datapack_id: str, **arguments: Any) -> Any:
        arguments["datapack_id"] = product_pack(datapack_id)
        started = time.monotonic()
        try:
            async with (
                asyncio.timeout(settings.meko_timeout_seconds),
                streamablehttp_client(
                    settings.meko_mcp_url,
                    headers=self.headers,
                    timeout=settings.meko_timeout_seconds,
                    sse_read_timeout=settings.meko_timeout_seconds,
                ) as (read, write, _),
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments)
            return decode_result(result)
        except MekoError:
            raise
        except Exception as exc:
            # A write may have reached the server. Never silently retry it.
            logger.warning("Meko %s interrupted (%s)", name, type(exc).__name__)
            raise MekoError("Meko operation was interrupted; its result is unconfirmed.") from exc
        finally:
            elapsed = time.monotonic() - started
            if elapsed >= 10:
                logger.warning("Meko %s took %.1f seconds", name, elapsed)

    async def save_turn(self, pack, agent, conversation, input, output, *, seed, metadata=None):
        await self.call(
            "conversation_add_message",
            datapack_id=pack,
            agent_id=agent,
            conversation_id=conversation,
            input=input,
            output=output,
            seed=seed,
            metadata=json.dumps(metadata or {}),
        )
        result = await self.call(
            "conversation_get",
            datapack_id=pack,
            agent_id=agent,
            conversation_id=conversation,
            include_messages=True,
        )

        def contains_turn(value):
            if isinstance(value, dict):
                if value.get("input") == input and (not output or value.get("output") == output):
                    return True
                return any(contains_turn(item) for item in value.values())
            return isinstance(value, list) and any(contains_turn(item) for item in value)

        if not contains_turn(result):
            raise MekoError("Conversation save was not confirmed on readback.")
        return result

    async def ensure_datapack(self, name: str, description: str) -> str:
        # Resolve first: retries after a lost create response reuse the same pack and quota slot.
        result = await self.http("GET", "/datapacks", params={"name": name, "limit": 100})
        for row in result.get("items", []):
            if row.get("datapack_name") == name and row.get("grant") == "owner":
                return product_pack(row["datapack_id"])
        result = await self.http(
            "POST", "/datapacks", json={"name": name, "description": description}
        )
        return product_pack(result["datapack_id"])

    async def conversation(self, pack: str, agent: str, session: str, title: str) -> str:
        result = await self.call(
            "conversation_create",
            datapack_id=pack,
            agent_id=agent,
            session_id=session,
            title=title[:120],
        )
        container = result.get("conversation", result.get("data", result))
        identifier = container.get("id") or container.get("conversation_id")
        if not identifier:
            raise MekoError("Meko did not return a conversation identifier.")
        return str(identifier)

    async def list_memories(
        self, pack: str, *, page: int = 1, limit: int = 25, query: str | None = None
    ) -> dict:
        params: dict[str, Any] = {
            "datapack_id": product_pack(pack),
            "page": page,
            "page_size": limit,
        }
        if query:
            params["q"] = query
        return await self.http("GET", "/memories", params=params)

    async def upload(self, pack: str, filename: str, content: bytes) -> dict:
        # The documented HTTP upload returned 404 in the live service. Use Meko's
        # released MCP upload flow; its signed destination receives no product key.
        pack = product_pack(pack)
        digest = hashlib.sha256(content).hexdigest()
        agent = "openhuman:documents"
        conversation = await self.conversation(pack, agent, f"upload:{digest}", "Document upload")
        result = await self.call(
            "knowledgebase_upload_document",
            datapack_id=pack,
            agent_id=agent,
            conversation_id=conversation,
            filename=filename,
            size=len(content),
            content_hash=digest,
            content_head_base64=base64.b64encode(content[:3072]).decode(),
        )
        if not result.get("key"):
            raise MekoError("Meko did not return a document key.")
        if not result.get("already_uploaded"):
            url, fields = result.get("url"), result.get("fields")
            if (
                not isinstance(url, str)
                or not url.startswith("https://")
                or not isinstance(fields, dict)
            ):
                raise MekoError("Meko did not return a valid signed upload destination.")
            async with httpx.AsyncClient(
                timeout=settings.meko_timeout_seconds, transport=self.transport
            ) as client:
                try:
                    response = await client.post(
                        url, data=fields, files={"file": (filename, content)}
                    )
                    response.raise_for_status()
                except httpx.HTTPError as exc:
                    raise MekoError(
                        "The document upload was interrupted; its result is unconfirmed."
                    ) from exc
        return {"document_key": result["key"], "status": "processing"}

    async def document_status(self, pack: str, key: str) -> dict:
        return await self.http(
            "GET",
            f"/datapacks/{product_pack(pack)}/knowledge-bases/document-status",
            params={"document_key": key},
        )

    async def documents(self, pack: str, *, page: int = 1) -> dict:
        return await self.http(
            "GET",
            f"/datapacks/{product_pack(pack)}/knowledge-bases/documents",
            params={"page": page, "page_size": 100},
        )

    async def delete_document(self, pack: str, identifier: str) -> dict:
        return await self.http(
            "DELETE",
            f"/datapacks/{product_pack(pack)}/knowledge-bases/documents/{UUID(identifier)}",
        )

    async def delete_pack(self, pack: str) -> None:
        await self.http("DELETE", f"/datapacks/{product_pack(pack)}")


meko = MekoClient()
