from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.activity.schemas import ActivityFeedResponse, ActivityStatsResponse
from app.activity.service import get_activity_feed, get_activity_stats
from app.auth.models import User
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.memory.scopes import owned_org

router = APIRouter(prefix="/api/activity", tags=["activity"])


@router.get("", response_model=ActivityFeedResponse)
async def list_activity(
    organization_id: UUID = Query(...),
    event_types: list[str] | None = Query(None),
    employee_id: UUID | None = Query(None),
    employee_type: str | None = Query(None),
    q: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ActivityFeedResponse:
    await owned_org(db, organization_id, _current_user.id)
    return await get_activity_feed(
        db,
        organization_id,
        event_types=event_types,
        employee_id=employee_id,
        employee_type=employee_type,
        q=q,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )


@router.get("/stats", response_model=ActivityStatsResponse)
async def activity_stats(
    organization_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ActivityStatsResponse:
    await owned_org(db, organization_id, _current_user.id)
    return await get_activity_stats(db, organization_id)
