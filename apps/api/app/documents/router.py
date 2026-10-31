from uuid import UUID
from urllib.parse import quote
from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.documents.schemas import DocumentResponse
from app.memory_sources.service import create_file_source, delete_source, list_sources

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _to_document_response(source):
    return DocumentResponse(id=source.id, org_id=source.org_id, employee_id=source.employee_id,
        filename=source.title or "document", content_type=source.content_type,
        size_bytes=source.size_bytes, status=source.status, error_message=source.error_message,
        uploaded_at=source.created_at, source_type=source.source_type, source_url=source.source_url)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(organization_id: UUID = Query(...), employee_id: UUID | None = None,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return [_to_document_response(s) for s in await list_sources(db, organization_id, current_user.id,
                                                               employee_id=employee_id)]


@router.post("", response_model=DocumentResponse, status_code=201)
async def upload_document(organization_id: UUID = Form(...), file: UploadFile = File(...),
    employee_id: UUID | None = Form(None), db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    raw = await file.read(settings.max_document_bytes + 1)
    source = await create_file_source(db, organization_id, current_user.id,
        employee_id=employee_id, filename=file.filename or "notes.txt", content=raw,
        content_type=file.content_type)
    return _to_document_response(source)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: UUID, organization_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        removed = await delete_source(db, organization_id, doc_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if not removed:
        raise HTTPException(404, "Document not found")


@router.get("/{doc_id}/download")
async def download_document(doc_id: UUID, organization_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.memory_sources.service import get_source_model
    source = await get_source_model(db, organization_id, doc_id, current_user.id)
    if source is None:
        raise HTTPException(404, "Document not found")
    content = source.content_bytes
    if content is None:
        content = (source.content_text or "").encode("utf-8")
    return StreamingResponse(BytesIO(content), media_type=source.content_type or "text/plain",
        headers={"Content-Disposition": "attachment; filename*=UTF-8\'\'" + quote(source.title or "document")})
