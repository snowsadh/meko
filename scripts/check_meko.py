"""Live product-client check using synthetic data, never the coding conversation.

Reuses two named demo datapacks. Datapack creation consumes a lifetime quota slot,
so these packs are deliberately retained between runs. Run from the repo root:
    uv run --project apps/api python scripts/check_meko.py
"""

import asyncio
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/api"))
from app.core.meko import MekoError, meko
from app.memory.service import search_rows, normalize_hit


async def main():
    company = await meko.ensure_datapack(
        "oh-demo-company", "OpenHuman reusable synthetic company demo"
    )
    employee = await meko.ensure_datapack(
        "oh-demo-support", "OpenHuman reusable synthetic support demo"
    )
    assert company != employee
    print(
        "Company and employee datapacks connected (reused on later runs).", flush=True
    )
    marker = uuid4().hex[:12]
    agent = "openhuman:demo-support"
    conversation = await meko.conversation(
        employee, agent, f"demo:{marker}", "Synthetic integration check"
    )
    company_conversation = await meko.conversation(
        company, agent, f"demo:{marker}", "Synthetic company lookup"
    )
    text = f"The synthetic Zephyr-{marker} queue owner is Nila."
    await meko.call(
        "memory_add",
        datapack_id=employee,
        agent_id=agent,
        conversation_id=conversation,
        text=text,
    )
    found = search_rows(
        await meko.call(
            "memory_search",
            datapack_id=employee,
            agent_id=agent,
            conversation_id=conversation,
            query=text,
            run_id=conversation,
            limit=10,
        )
    )
    assert found, "Meko did not return the saved fact on readback"
    for hit in found:
        normalize_hit(hit, "employee_memory", {})
    print("Explicit fact extraction and scoped search passed.", flush=True)
    listing = await meko.list_memories(employee)
    assert "memories" in listing, f"Unexpected memory list fields: {list(listing)}"
    company_hits = search_rows(
        await meko.call(
            "memory_search",
            datapack_id=company,
            agent_id=agent,
            conversation_id=company_conversation,
            query=text,
            limit=10,
        )
    )
    assert all(marker not in json.dumps(hit) for hit in company_hits), (
        "Private fact leaked into company pack"
    )
    content = f"# Synthetic support guide\n\nZephyr-{marker} support hours are 09:00–17:00 UTC.\n".encode()
    filename = hashlib.sha256(content).hexdigest() + ".md"
    uploaded = await meko.upload(employee, filename, content)
    key = uploaded["document_key"]
    for _ in range(24):
        status = await meko.document_status(employee, key)
        if status.get("document_status") in {"COMPLETED", "FAILED"}:
            break
        await asyncio.sleep(5)
    assert status.get("document_status") == "COMPLETED", (
        f"Document processing: {status.get('document_status')}"
    )
    files = await meko.documents(employee)
    document = next(
        row
        for row in files["items"]
        if row["document_name"].rsplit("/", 1)[-1] == filename
    )
    hits = search_rows(
        await meko.call(
            "knowledgebase_search",
            datapack_id=employee,
            agent_id=agent,
            conversation_id=conversation,
            query=f"Zephyr-{marker} support hours",
            limit=5,
        )
    )
    assert any(marker in json.dumps(hit) for hit in hits), (
        "Indexed guide was not recalled"
    )
    for hit in hits:
        normalize_hit(hit, "employee_document", {})
    print("Private document upload, indexing, and recall passed.", flush=True)
    # A single synthetic exchange checks transport, not a promise that extraction finished.
    await meko.call(
        "conversation_add_message",
        datapack_id=employee,
        agent_id=agent,
        conversation_id=conversation,
        input="This is a synthetic integration check.",
        output="Confirmed. No real customer information is included.",
        seed=f"demo:{marker}",
    )
    for fact in found:
        identifier = fact.get("id") or fact.get("memory_id")
        assert identifier, "Fact has no identifier"
        await meko.call(
            "memory_update",
            datapack_id=employee,
            agent_id=agent,
            conversation_id=conversation,
            memory_id=identifier,
            text=f"Synthetic Zephyr-{marker} queue owner is Omar.",
        )
        updated = await meko.list_memories(employee, query=marker)
        assert any("Omar" in json.dumps(row) for row in updated["memories"]), (
            "Correction readback failed"
        )
        await meko.call(
            "memory_delete_by_id",
            datapack_id=employee,
            agent_id=agent,
            conversation_id=conversation,
            memory_id=identifier,
        )
        after = await meko.list_memories(employee, query=marker)
        assert all(
            str(row.get("id")) != str(identifier) for row in after["memories"]
        ), "Deletion readback failed"
    deleted = await meko.delete_document(employee, document["id"])
    assert deleted.get("s3_deleted") is not False, (
        "Meko reports a partial document deletion"
    )
    print(
        "Conversation transport, fact correction/forget, and document removal passed.",
        flush=True,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except MekoError as error:
        raise SystemExit(
            f"Live check stopped: {error}. No automatic retry; synthetic demo resources may remain."
        ) from error
