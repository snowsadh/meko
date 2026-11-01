from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.build import run_agent, capture_run
from app.agent.models import AgentFile, AgentRun
from app.agent.schemas import AgentMessageRequest, AgentMessageResponse
from app.auth.models import User
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.memory.scopes import owned_employee

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get(
    "/files/{file_id}", response_class=Response,
    responses={200: {"content": {"application/octet-stream": {
        "schema": {"type": "string", "format": "binary"},
    }}}},
)
async def download_file(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file = await db.get(AgentFile, file_id)
    if file is None:
        raise HTTPException(404, "File not found")
    run = await db.get(AgentRun, file.run_id)
    await owned_employee(db, run.org_id, run.employee_id, current_user.id)
    return Response(content=file.content, media_type=file.media_type, headers={
        "Content-Disposition": f'attachment; filename="{file.filename}"',
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox; default-src 'none'",
        "X-Content-SHA256": file.sha256,
    })


@router.post("/message", response_model=AgentMessageResponse)
async def message(
    data: AgentMessageRequest,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = await run_agent(
        db,
        org_id=data.org_id,
        employee_id=data.employee_id,
        user_id=current_user.id,
        message=data.message,
        thread_key=data.thread_key,
        request_key=str(data.request_key) if data.request_key else None,
        use_meko=data.use_meko,
        allow_external_tools=data.allow_tools,
    )
    if run.capture_status == "pending":
        background.add_task(capture_run, run.id)
    return run


@router.get("/runs", response_model=list[AgentMessageResponse])
async def runs(
    org_id: UUID,
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await owned_employee(db, org_id, employee_id, current_user.id)
    return list(
        (
            await db.scalars(
                select(AgentRun)
                .where(AgentRun.org_id == org_id, AgentRun.employee_id == employee_id)
                .order_by(AgentRun.created_at.desc())
                .limit(30)
            )
        ).all()
    )


@router.post("/runs/{run_id}/capture", response_model=AgentMessageResponse)
async def retry_capture(
    run_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    run = await db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    await owned_employee(db, run.org_id, run.employee_id, current_user.id)
    if run.capture_status in {"skipped", "router"}:
        raise HTTPException(409, "Memory capture was disabled for this run.")
    await capture_run(run.id)
    await db.refresh(run)
    return run
