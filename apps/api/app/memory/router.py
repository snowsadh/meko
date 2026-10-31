from __future__ import annotations

from uuid import UUID
from typing import Literal
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.memory.schemas import (
    CreateMemoryTextRequest,
    CreateMemoryUrlRequest,
    MemorySearchRequest,
    MemorySearchResponse,
)
from app.memory.service import (
    create_text_memory,
    create_url_memory,
    delete_memory_source,
    list_memory_sources,
    retry_memory_source,
    search_memory,
)
from app.memory_sources.schemas import MemorySourceResponse

router = APIRouter(prefix="/api/organizations/{org_id}/memory", tags=["memory"])


class FactRequest(BaseModel):
    employee_id: UUID
    text: str = Field(min_length=1, max_length=8000)
    operation_id: UUID | None = None


class ShareRequest(BaseModel):
    employee_id: UUID
    expected_text: str = Field(min_length=1, max_length=8000)
    confirmed: Literal[True]


@router.post("/facts")
async def remember_fact(org_id: UUID, data: FactRequest, db: AsyncSession = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    from app.memory.service import remember
    return await remember(db, org_id, data.employee_id, current_user.id, data.text,
                           operation_id=str(data.operation_id) if data.operation_id else None)


@router.patch("/facts/{memory_id}")
async def correct_fact(org_id: UUID, memory_id: UUID, data: FactRequest,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.memory.service import change_fact
    return await change_fact(db, org_id, data.employee_id, current_user.id, memory_id, text=data.text)


@router.delete("/facts/{memory_id}")
async def forget_fact(org_id: UUID, memory_id: UUID, employee_id: UUID,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.memory.service import change_fact
    return await change_fact(db, org_id, employee_id, current_user.id, memory_id)


@router.post("/facts/{memory_id}/share", response_model=MemorySourceResponse)
async def publish_fact(org_id: UUID, memory_id: UUID, data: ShareRequest,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.memory.service import share_fact
    return await share_fact(db, org_id, data.employee_id, current_user.id,
                             memory_id, data.expected_text)


@router.post("/text", response_model=MemorySourceResponse, status_code=status.HTTP_201_CREATED)
async def create_text_memory_route(
    org_id: UUID,
    data: CreateMemoryTextRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemorySourceResponse:
    source = await create_text_memory(db, org_id, current_user.id, data)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return MemorySourceResponse.model_validate(source)


@router.post("/url", response_model=MemorySourceResponse, status_code=status.HTTP_201_CREATED)
async def create_url_memory_route(
    org_id: UUID,
    data: CreateMemoryUrlRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemorySourceResponse:
    source = await create_url_memory(db, org_id, current_user.id, data)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return MemorySourceResponse.model_validate(source)


@router.post("/search", response_model=MemorySearchResponse)
async def search_memory_route(
    org_id: UUID,
    data: MemorySearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemorySearchResponse:
    response = await search_memory(db, org_id, current_user.id, data)
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization or employee not found",
        )
    return response


@router.get("/sources", response_model=list[MemorySourceResponse])
async def list_memory_sources_route(
    org_id: UUID,
    employee_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MemorySourceResponse]:
    sources = await list_memory_sources(db, org_id, current_user.id, employee_id=employee_id)
    if sources is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization or employee not found",
        )
    return [MemorySourceResponse.model_validate(source) for source in sources]


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory_source_route(
    org_id: UUID,
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        deleted = await delete_memory_source(db, org_id, source_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")


@router.post("/sources/{source_id}/retry", response_model=MemorySourceResponse)
async def retry_memory_source_route(
    org_id: UUID,
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemorySourceResponse:
    try:
        source = await retry_memory_source(db, org_id, source_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return MemorySourceResponse.model_validate(source)
