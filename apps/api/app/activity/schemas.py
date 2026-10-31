from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ActivityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    event_type: str
    summary: str
    description: str | None = None
    employee_id: UUID | None = None
    employee_name: str | None = None
    platform: str | None = None
    status: str | None = None
    metadata: dict | None = None
    occurred_at: datetime


class ActivityFeedResponse(BaseModel):
    events: list[ActivityEventResponse]
    total: int
    next_offset: int | None = None


class ActivityStatsResponse(BaseModel):
    total_today: int
    agent_runs: int
    source_ingests: int
    employee_events: int
    tool_usages: int
    human_escalations: int
    memory_operations: int
