from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.memory_sources.schemas import (
    CreateTextMemorySourceRequest,
    CreateUrlMemorySourceRequest,
    MemorySourceResponse,
)
from app.memory_sources.service import (
    create_text_source,
    create_url_source,
    delete_source,
    list_sources,
    retry_source,
)

router = APIRouter(
    prefix="/api/organizations/{org_id}/memory-sources",
    tags=["memory-sources"],
)


@router.post("/text", response_model=MemorySourceResponse, status_code=status.HTTP_201_CREATED)
async def create_text_source_route(
    org_id: UUID,
    data: CreateTextMemorySourceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemorySourceResponse:
    source = await create_text_source(
        db,
        org_id,
        current_user.id,
        scope=data.scope,
        employee_id=data.employee_id,
        title=data.title,
        content_text=data.content_text,
    )
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization or employee not found",
        )
    return MemorySourceResponse.model_validate(source)


@router.post("/url", response_model=MemorySourceResponse, status_code=status.HTTP_201_CREATED)
async def create_url_source_route(
    org_id: UUID,
    data: CreateUrlMemorySourceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemorySourceResponse:
    source = await create_url_source(
        db,
        org_id,
        current_user.id,
        scope=data.scope,
        employee_id=data.employee_id,
        title=data.title,
        source_url=data.source_url,
    )
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization or employee not found",
        )
    return MemorySourceResponse.model_validate(source)


@router.get("", response_model=list[MemorySourceResponse])
async def list_sources_route(
    org_id: UUID,
    employee_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MemorySourceResponse]:
    sources = await list_sources(db, org_id, current_user.id, employee_id=employee_id)
    if sources is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization or employee not found",
        )
    return [MemorySourceResponse.model_validate(source) for source in sources]


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source_route(
    org_id: UUID,
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        deleted = await delete_source(db, org_id, source_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")


@router.post("/{source_id}/retry", response_model=MemorySourceResponse)
async def retry_source_route(
    org_id: UUID,
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemorySourceResponse:
    try:
        source = await retry_source(db, org_id, source_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return MemorySourceResponse.model_validate(source)
