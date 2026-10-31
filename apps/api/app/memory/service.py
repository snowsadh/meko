from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.core.meko import MekoError, meko
from app.memory.scopes import employee_agent, owned_employee, owned_org, require_pack
from app.memory.schemas import MemorySearchResponse, MemorySearchResultResponse
from app.memory_sources.models import MemorySource
from app.memory_sources.service import (
    create_text_source,
    create_url_source,
    delete_source,
    list_sources,
    retry_source,
)


async def create_text_memory(db, org_id, user_id, data, **_):
    return await create_text_source(
        db,
        org_id,
        user_id,
        scope=data.scope,
        employee_id=data.employee_id,
        title=data.title,
        content_text=data.content_text,
    )


async def create_url_memory(db, org_id, user_id, data, **_):
    return await create_url_source(
        db,
        org_id,
        user_id,
        scope=data.scope,
        employee_id=data.employee_id,
        title=data.title,
        source_url=data.source_url,
    )


async def list_memory_sources(db, org_id, user_id, *, employee_id=None):
    return await list_sources(db, org_id, user_id, employee_id=employee_id)


async def delete_memory_source(db, org_id, source_id, user_id, **_):
    return await delete_source(db, org_id, source_id, user_id)


async def retry_memory_source(db, org_id, source_id, user_id, **_):
    return await retry_source(db, org_id, source_id, user_id)


def search_rows(result):
    if isinstance(result, list):
        return result
    for name in ("results", "matches", "memories"):
        if name in result and isinstance(result[name], list):
            return result[name]
    raise MekoError("Meko returned an unrecognised search shape; context was not assumed empty.")


def normalize_hit(item, source, labels):
    metadata = item.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    identifier = (
        item.get("id") or item.get("memory_id") or item.get("chunk_id") or item.get("document_id")
    )
    content = (
        item.get("content")
        or item.get("chunk_text")
        or item.get("text")
        or item.get("memory")
        or item.get("data")
    )
    document_id = item.get("document_id") or metadata.get("document_id")
    if not identifier or not isinstance(content, str):
        raise MekoError("Meko search returned a source without identifiable text.")
    score = item.get("score", item.get("rerank_score"))
    return MemorySearchResultResponse(
        provider_result_id=str(identifier),
        document_id=str(document_id) if document_id else None,
        container_tag=source,
        score=score if isinstance(score, (int, float)) else None,
        content=content,
        metadata={
            **metadata,
            "source": source,
            "title": labels.get(str(document_id))
            or item.get("filename")
            or source.replace("_", " "),
        },
    )


async def recall(db, org, emp, query, *, conversation_id, session_key, limit=5):
    private_pack, company_pack = require_pack(emp), require_pack(org)
    if private_pack == company_pack:
        raise MekoError("Employee and company knowledge must use different datapacks.")
    agent = employee_agent(emp.id)
    shared_conversation = await meko.conversation(
        company_pack, agent, f"company:{emp.id}:{session_key}", "Company knowledge lookup"
    )
    searches = [
        ("employee_memory", private_pack, "memory_search", conversation_id),
        ("employee_document", private_pack, "knowledgebase_search", conversation_id),
        ("company_document", company_pack, "knowledgebase_search", shared_conversation),
    ]
    responses = await asyncio.gather(
        *[
            meko.call(
                tool,
                datapack_id=pack,
                agent_id=agent,
                conversation_id=conv,
                query=query,
                limit=limit,
            )
            for _, pack, tool, conv in searches
        ]
    )
    sources = (
        await db.scalars(
            select(MemorySource).where(
                MemorySource.org_id == org.id,
                (MemorySource.employee_id == emp.id) | MemorySource.employee_id.is_(None),
            )
        )
    ).all()
    labels = {s.meko_document_id: s.title for s in sources if s.meko_document_id}
    hits = []
    for (source, _, _, _), response in zip(searches, responses):
        hits.extend(
            normalize_hit(row, source, labels).model_dump(mode="json")
            for row in search_rows(response)
        )
    return hits


async def search_memory(db, org_id, user_id, data, **_):
    if data.employee_id:
        org, emp = await owned_employee(db, org_id, data.employee_id, user_id)
        key = str(uuid4())
        conv = await meko.conversation(
            require_pack(emp), employee_agent(emp.id), key, "Memory search"
        )
        hits = await recall(
            db,
            org,
            emp,
            data.query,
            conversation_id=conv,
            session_key=key,
            limit=min(data.limit, 10),
        )
    else:
        org = await owned_org(db, org_id, user_id)
        conv = await meko.conversation(
            require_pack(org), "openhuman:company", str(uuid4()), "Company search"
        )
        result = await meko.call(
            "knowledgebase_search",
            datapack_id=require_pack(org),
            agent_id="openhuman:company",
            conversation_id=conv,
            query=data.query,
            limit=min(data.limit, 10),
        )
        hits = [
            normalize_hit(r, "company_document", {}).model_dump(mode="json")
            for r in search_rows(result)
        ]
    return MemorySearchResponse(query=data.query, tags=[], results=hits, total=len(hits))


async def find_fact(emp, memory_id):
    page = 1
    while True:
        result = await meko.list_memories(require_pack(emp), page=page, limit=100)
        for item in result.get("memories", []):
            if str(item.get("id")) == str(memory_id):
                return item
        if page >= result.get("total_pages", 1):
            break
        page += 1
    raise HTTPException(404, "Memory not found in this employee's datapack")


async def remember(db, org_id, employee_id, user_id, text, *, operation_id=None):
    _, emp = await owned_employee(db, org_id, employee_id, user_id)
    pack, agent = require_pack(emp), employee_agent(emp.id)
    operation_id = operation_id or str(uuid4())
    conv = await meko.conversation(
        pack, agent, f"remember:{operation_id}", "Explicitly remembered fact"
    )
    result = await meko.call(
        "memory_add", datapack_id=pack, agent_id=agent, conversation_id=conv, text=text
    )
    # Inspect the exact stored facts from this operation, not an unrelated recent window.
    verification = await meko.call(
        "memory_search",
        datapack_id=pack,
        agent_id=agent,
        conversation_id=conv,
        query=text,
        run_id=conv,
        limit=10,
    )
    facts = search_rows(verification)
    if not facts:
        raise MekoError("No stored fact was returned on readback. Remembering is not confirmed.")
    return {"facts": facts, "conversation_id": conv, "result": result}


async def withdraw_shared_copies(db, org_id, employee_id, memory_id, user_id):
    copies = list(
        (
            await db.scalars(
                select(MemorySource).where(
                    MemorySource.org_id == org_id,
                    MemorySource.origin_employee_id == employee_id,
                    MemorySource.origin_memory_id == str(memory_id),
                )
            )
        ).all()
    )
    for source in copies:
        await delete_source(db, org_id, source.id, user_id)
    return len(copies)


async def change_fact(db, org_id, employee_id, user_id, memory_id, *, text=None):
    _, emp = await owned_employee(db, org_id, employee_id, user_id)
    row = await find_fact(emp, memory_id)
    agent = row.get("agent_id") or employee_agent(emp.id)
    pack = require_pack(emp)
    conv = await meko.conversation(pack, agent, f"edit:{uuid4()}", "Memory correction or removal")
    # Withdrawing a published copy is visible and explicit in the UI. If it fails,
    # keep the private fact so an old public copy is not silently left behind.
    copies = await withdraw_shared_copies(db, org_id, employee_id, memory_id, user_id)
    args = {"memory_id": str(memory_id), "agent_id": agent, "conversation_id": conv}
    if text is not None:
        args["text"] = text
    await meko.call(
        "memory_update" if text is not None else "memory_delete_by_id", datapack_id=pack, **args
    )
    if text is not None:
        verified = await find_fact(emp, memory_id)
        if verified.get("data", verified.get("memory")) != text:
            raise MekoError("The corrected text was not confirmed on readback.")
    else:
        try:
            await find_fact(emp, memory_id)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
        else:
            raise MekoError("Meko still lists this fact; forgetting is not confirmed.")
    emp.context_version += 1
    await db.commit()
    return {
        "status": "corrected" if text is not None else "forgotten",
        "withdrawn_shared_copies": copies,
    }


async def share_fact(db, org_id, employee_id, user_id, memory_id, expected_text):
    org, emp = await owned_employee(db, org_id, employee_id, user_id)
    row = await find_fact(emp, memory_id)
    text = row.get("data", row.get("memory"))
    if not isinstance(text, str) or text != expected_text:
        raise HTTPException(409, "This memory changed. Review its current text before sharing.")
    # This is an explicit, attributable cross-pack publication, not native promotion.
    from app.memory_sources.service import create_file_source

    content = (
        f"# Company lesson\n\n{text}\n\nSource employee: {emp.name}\nSource memory: {memory_id}\n"
    )
    source = await create_file_source(
        db,
        org.id,
        user_id,
        employee_id=None,
        filename=f"lesson-{memory_id}.md",
        content=content.encode(),
        content_type="text/markdown",
        origin_memory_id=str(memory_id),
        origin_employee_id=emp.id,
    )
    return source
