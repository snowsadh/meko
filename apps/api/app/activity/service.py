from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.activity.models import ActivityEvent
from app.activity.schemas import ActivityEventResponse, ActivityFeedResponse, ActivityStatsResponse
from app.agent.jobs.models import AgentJob
from app.agent.models import AgentRun
from app.employees.models import Employee
from app.memory_sources.models import MemorySource

logger = logging.getLogger(__name__)
_ALLOWED_EVENT_TYPES = frozenset({
    "agent_run", "agent_conversation", "employee_created", "employee_updated",
    "tool_usage", "human_escalation", "memory_operation", "memory_source",
    "mcp_connected", "org_created", "org_updated", "org_deleted",
    "slack_oauth", "channel_assigned", "channel_unassigned",
})


async def record_activity(db: AsyncSession, org_id: UUID, event_type: str, summary: str, *,
                          employee_id: UUID | None = None, employee_name: str | None = None,
                          platform: str | None = None, status: str | None = None,
                          description: str | None = None, metadata: dict | None = None,
                          occurred_at: datetime | None = None) -> ActivityEvent:
    event = ActivityEvent(org_id=org_id, event_type=event_type, summary=summary,
                          employee_id=employee_id, employee_name=employee_name,
                          platform=platform, status=status, description=description,
                          metadata_=metadata, occurred_at=occurred_at or datetime.now(timezone.utc))
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def record_activity_from_context(event_type: str, summary: str, **kwargs: object) -> None:
    try:
        from app.activity.context import activity_employee_id, activity_employee_name, activity_org_id, activity_platform
        from app.core.database import async_session_factory
        org_id = activity_org_id.get()
        if not org_id:
            return
        async with async_session_factory() as db:
            await record_activity(db, UUID(org_id), event_type, summary,
                                  employee_id=UUID(activity_employee_id.get()) if activity_employee_id.get() else None,
                                  employee_name=activity_employee_name.get(), platform=activity_platform.get(), **kwargs)
    except Exception:
        logger.debug("Unable to record contextual activity", exc_info=True)


def _event_from_model(event_id: str, event_type: str, summary: str, occurred_at: datetime,
                      *, employee_id: UUID | None = None, employee_name: str | None = None,
                      status: str | None = None, platform: str | None = None,
                      description: str | None = None, metadata: dict | None = None) -> ActivityEventResponse:
    return ActivityEventResponse(id=event_id, event_type=event_type, summary=summary,
                                 occurred_at=occurred_at, employee_id=employee_id,
                                 employee_name=employee_name, status=status, platform=platform,
                                 description=description, metadata=metadata)


async def get_activity_feed(db: AsyncSession, org_id: UUID, *, event_types: list[str] | None = None,
                            employee_id: UUID | None = None, employee_type: str | None = None,
                            q: str | None = None, date_from: datetime | None = None,
                            date_to: datetime | None = None, offset: int = 0, limit: int = 50) -> ActivityFeedResponse:
    allowed = [value for value in (event_types or []) if value in _ALLOWED_EVENT_TYPES]
    employees = {e.id: e for e in (await db.scalars(select(Employee).where(Employee.org_id == org_id))).all()}
    rows: list[ActivityEventResponse] = []
    recorded = (await db.scalars(select(ActivityEvent).where(ActivityEvent.org_id == org_id))).all()
    for event in recorded:
        rows.append(_event_from_model(f"recorded:{event.id}", event.event_type, event.summary, event.occurred_at,
                                      employee_id=event.employee_id, employee_name=event.employee_name,
                                      status=event.status, platform=event.platform, description=event.description,
                                      metadata=event.metadata_))
    sources = (await db.scalars(select(MemorySource).where(MemorySource.org_id == org_id))).all()
    for source in sources:
        employee = employees.get(source.employee_id) if source.employee_id else None
        rows.append(_event_from_model(f"memory_source:{source.id}", "memory_source",
                                      f"{source.source_type.title()} source {source.status}", source.created_at,
                                      employee_id=source.employee_id, employee_name=employee.name if employee else None,
                                      status=source.status, metadata={"scope": source.scope, "title": source.title}))
    for employee in employees.values():
        rows.append(_event_from_model(f"employee_created:{employee.id}", "employee_created",
                                      f'Employee "{employee.name}" created', employee.created_at,
                                      employee_id=employee.id, employee_name=employee.name, status=employee.status,
                                      metadata={"employee_type": employee.employee_type, "role": employee.role}))
    jobs = (await db.scalars(select(AgentJob).where(AgentJob.employee_id.in_(employees or {UUID(int=0)})))).all()
    for job in jobs:
        employee = employees.get(job.employee_id)
        kind = "tool_usage" if job.job_type in {"web_search", "calculate", "fetch_url"} else "agent_run"
        rows.append(_event_from_model(f"agent_job:{job.id}", kind, job.user_text or job.job_type,
                                      job.created_at, employee_id=job.employee_id,
                                      employee_name=employee.name if employee else None, platform=job.platform,
                                      status=job.status, metadata={"job_type": job.job_type}))
    runs = (await db.scalars(select(AgentRun).where(AgentRun.org_id == org_id))).all()
    for run in runs:
        employee = employees.get(run.employee_id)
        rows.append(_event_from_model(f"agent_run:{run.id}", "agent_run", run.input, run.created_at,
            employee_id=run.employee_id, employee_name=employee.name if employee else None,
            platform=run.platform, status=run.status, metadata={"capture_status": run.capture_status,
                "delivery_status": run.delivery_status, "recalled_count": len(run.recalled)}))
    rows = [e for e in rows if (not allowed or e.event_type in allowed)
            and (employee_id is None or e.employee_id == employee_id)
            and (employee_type is None or (employees.get(e.employee_id).employee_type if e.employee_id in employees else None) == employee_type)
            and (not q or q.lower() in f"{e.summary} {e.description or ''}".lower())
            and (date_from is None or e.occurred_at >= date_from)
            and (date_to is None or e.occurred_at <= date_to)]
    rows.sort(key=lambda e: e.occurred_at, reverse=True)
    total = len(rows)
    page = rows[offset:offset + limit]
    return ActivityFeedResponse(events=page, total=total, next_offset=offset + limit if offset + limit < total else None)


async def get_activity_stats(db: AsyncSession, org_id: UUID) -> ActivityStatsResponse:
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    feed = await get_activity_feed(db, org_id, date_from=today, limit=10000)
    events = feed.events
    return ActivityStatsResponse(total_today=len(events),
        agent_runs=sum(e.event_type == "agent_run" for e in events),
        source_ingests=sum(e.event_type == "memory_source" for e in events),
        employee_events=sum(e.event_type.startswith("employee_") for e in events),
        tool_usages=sum(e.event_type == "tool_usage" for e in events),
        human_escalations=sum(e.event_type == "human_escalation" for e in events),
        memory_operations=sum(e.event_type == "memory_operation" for e in events))
