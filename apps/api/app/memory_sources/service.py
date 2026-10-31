from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.meko import MekoError, meko
from app.memory.scopes import owned_org, owned_employee, require_pack
from app.memory_sources.models import MemorySource

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".text", ".md", ".csv", ".json", ".xml", ".html", ".htm"}


async def ensure_owned_org(db, org_id, user_id):
    return await owned_org(db, org_id, user_id)


async def ensure_owned_employee(db, org_id, employee_id):
    from app.employees.models import Employee

    emp = await db.scalar(
        select(Employee).where(Employee.id == employee_id, Employee.org_id == org_id)
    )
    if emp is None:
        raise HTTPException(404, "Employee not found")
    return emp


async def source_pack(db, org_id, user_id, employee_id=None):
    if employee_id:
        _, emp = await owned_employee(db, org_id, employee_id, user_id)
        return require_pack(emp)
    return require_pack(await owned_org(db, org_id, user_id))


async def get_source_model(db, org_id, source_id, user_id):
    await owned_org(db, org_id, user_id)
    return await db.scalar(
        select(MemorySource).where(MemorySource.id == source_id, MemorySource.org_id == org_id)
    )


async def refresh_source(db, org_id, source_id, user_id):
    source = await get_source_model(db, org_id, source_id, user_id)
    if source is not None and source.status == "pending":
        await _refresh(source)
        await db.commit()
    return source


async def _upload(source):
    raw = source.content_bytes
    if raw is None and source.content_text is not None:
        raw = source.content_text.encode("utf-8")
    if not raw or not source.meko_datapack_id:
        raise ValueError("This source has no Meko upload. Re-upload the original file.")
    suffix = Path(source.title or "notes.txt").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        suffix = ".txt"
    # A deterministic physical filename lets the paginated file API resolve the exact
    # document ID even when people upload different files with the same display name.
    filename = f"{source.content_hash}{suffix}"
    result = await meko.upload(source.meko_datapack_id, filename, raw)
    source.meko_document_key = result["document_key"]
    source.status = "pending"
    source.error_message = None


async def _refresh(source):
    if not source.meko_document_key or not source.meko_datapack_id:
        return
    result = await meko.document_status(source.meko_datapack_id, source.meko_document_key)
    state = result.get("document_status")
    if state not in {"NOT_STARTED", "QUEUED", "PROCESSING", "COMPLETED", "FAILED", "RETRY"}:
        raise MekoError("Meko returned an unknown document processing state.")
    source.status = "failed" if state == "FAILED" else "pending"
    source.error_message = "Meko could not index this file." if state == "FAILED" else None
    if state in {"COMPLETED", "FAILED"}:
        filename = source.meko_document_key.rsplit("/", 1)[-1]
        page = 1
        while True:
            listing = await meko.documents(source.meko_datapack_id, page=page)
            for item in listing.get("items", []):
                if str(item.get("document_name", "")).rsplit("/", 1)[-1] == filename:
                    source.meko_document_id = item["id"]
                    source.status = "indexed" if state == "COMPLETED" else "failed"
                    return
            if not listing.get("has_more"):
                break
            page += 1
        source.error_message = "Indexing finished; waiting for the file identifier."


async def create_file_source(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    *,
    employee_id: UUID | None,
    filename: str,
    content: bytes,
    content_type: str | None = None,
    origin_memory_id: str | None = None,
    origin_employee_id: UUID | None = None,
) -> MemorySource:
    pack = await source_pack(db, org_id, user_id, employee_id)
    filename = Path(filename).name
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(422, "Upload a PDF, Markdown, or supported UTF-8 text file.")
    if not content or len(content) > settings.max_document_bytes:
        raise HTTPException(413, "The file must contain between 1 byte and 5 MB.")
    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise HTTPException(422, "The file does not contain a PDF header.")
    else:
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(422, "Text documents must use UTF-8.") from exc
    digest = hashlib.sha256(content).hexdigest()
    existing = await db.scalar(
        select(MemorySource).where(
            MemorySource.meko_datapack_id == pack, MemorySource.content_hash == digest
        )
    )
    if existing:
        return existing
    source = MemorySource(
        id=uuid4(),
        org_id=org_id,
        employee_id=employee_id,
        scope="employee" if employee_id else "org",
        source_type="file",
        title=filename,
        content_bytes=content,
        content_type=content_type or "application/octet-stream",
        size_bytes=len(content),
        content_hash=digest,
        meko_datapack_id=pack,
        origin_memory_id=origin_memory_id,
        origin_employee_id=origin_employee_id,
        status="pending",
        created_by_user_id=user_id,
    )
    db.add(source)
    await db.commit()
    try:
        await _upload(source)
    except MekoError as exc:
        source.status = "failed"
        source.error_message = str(exc)
    await db.commit()
    await db.refresh(source)
    return source


async def create_text_source(db, org_id, user_id, *, scope, employee_id, title, content_text, **_):
    if scope == "org" and employee_id:
        raise HTTPException(422, "Company sources cannot target an employee.")
    if scope == "employee" and not employee_id:
        raise HTTPException(422, "Choose an employee for this source.")
    filename = title or "notes.txt"
    if Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
        filename += ".txt"
    return await create_file_source(
        db,
        org_id,
        user_id,
        employee_id=employee_id,
        filename=filename,
        content=content_text.encode("utf-8"),
        content_type="text/plain",
    )


async def create_url_source(*args, **kwargs):
    raise HTTPException(422, "Website importing is not supported. Upload a document instead.")


async def list_sources(db, org_id, user_id, *, employee_id=None):
    await owned_org(db, org_id, user_id)
    statement = select(MemorySource).where(MemorySource.org_id == org_id)
    if employee_id:
        await owned_employee(db, org_id, employee_id, user_id)
        statement = statement.where(MemorySource.employee_id == employee_id)
    sources = list((await db.scalars(statement.order_by(MemorySource.created_at.desc()))).all())
    for source in sources:
        if source.status == "pending" and source.meko_document_key:
            try:
                await _refresh(source)
            except MekoError as exc:
                source.error_message = str(exc)
    await db.commit()
    return sources


async def delete_source(db, org_id, source_id, user_id, **_):
    source = await get_source_model(db, org_id, source_id, user_id)
    if source is None:
        return False
    if not source.meko_datapack_id or not source.meko_document_key:
        if source.status == "failed" and not source.provider_memory_id:
            # A failed upload may still have arrived: send the same bytes once to resolve
            # its content-addressed key before deleting. Do not claim a local hide is remote deletion.
            await _upload(source)
            await db.commit()
        else:
            raise ValueError(
                "Remote file identity is unavailable; re-upload or resolve setup first."
            )
    if not source.meko_document_id:
        await _refresh(source)
        await db.commit()
    if not source.meko_document_id:
        raise ValueError("The file is still processing. Remove it once indexing finishes.")
    result = await meko.delete_document(source.meko_datapack_id, source.meko_document_id)
    if result.get("s3_deleted") is False:
        source.status = "failed"
        source.error_message = (
            "Search entries were removed, but Meko reports the stored file remains."
        )
        await db.commit()
        raise MekoError(source.error_message)
    await db.delete(source)
    await db.commit()
    return True


async def retry_source(db, org_id, source_id, user_id, **_):
    source = await get_source_model(db, org_id, source_id, user_id)
    if source is None:
        return None
    if source.status != "failed":
        raise ValueError("Only failed uploads can be retried.")
    await _upload(source)
    await db.commit()
    await db.refresh(source)
    return source
