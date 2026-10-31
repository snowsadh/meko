from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.activity.service import record_activity
from app.auth.models import User
from app.channel_assignments.models import ChannelAssignment
from app.channel_assignments.schemas import ChannelAssignmentResponse, CreateChannelAssignmentRequest
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.employees.models import Employee
from app.organizations.models import Organization

router = APIRouter(prefix="/api/organizations/{org_id}/employees/{emp_id}/channel-assignments", tags=["channel-assignments"])
_ALLOWED_PLATFORMS = {"discord", "slack"}


async def _employee(db: AsyncSession, org_id: UUID, emp_id: UUID, user_id: UUID) -> Employee:
    org = await db.scalar(select(Organization).where(Organization.id == org_id, Organization.owner_id == user_id))
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    employee = await db.scalar(select(Employee).where(Employee.id == emp_id, Employee.org_id == org_id))
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.post("", response_model=ChannelAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(org_id: UUID, emp_id: UUID, data: CreateChannelAssignmentRequest,
                            db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if data.platform not in _ALLOWED_PLATFORMS:
        raise HTTPException(status_code=422, detail=f"platform must be one of {sorted(_ALLOWED_PLATFORMS)}")
    employee = await _employee(db, org_id, emp_id, current_user.id)
    assignment = ChannelAssignment(employee_id=emp_id, platform=data.platform, channel_id=data.channel_id,
                                   channel_name=data.channel_name)
    db.add(assignment)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Channel assignment already exists") from None
    await db.refresh(assignment)
    await record_activity(db, org_id, "channel_assigned", f"Channel assigned to {employee.name}",
                          employee_id=emp_id, employee_name=employee.name, platform=data.platform)
    return ChannelAssignmentResponse.model_validate(assignment)


@router.get("", response_model=list[ChannelAssignmentResponse])
async def list_assignments(org_id: UUID, emp_id: UUID, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    await _employee(db, org_id, emp_id, current_user.id)
    result = await db.scalars(select(ChannelAssignment).where(ChannelAssignment.employee_id == emp_id))
    return [ChannelAssignmentResponse.model_validate(item) for item in result]


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(org_id: UUID, emp_id: UUID, assignment_id: UUID,
                            db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    employee = await _employee(db, org_id, emp_id, current_user.id)
    assignment = await db.scalar(select(ChannelAssignment).where(ChannelAssignment.id == assignment_id,
                                                                  ChannelAssignment.employee_id == emp_id))
    if assignment is None:
        raise HTTPException(status_code=404, detail="Channel assignment not found")
    await db.delete(assignment)
    await db.commit()
    await record_activity(db, org_id, "channel_unassigned", f"Channel unassigned from {employee.name}",
                          employee_id=emp_id, employee_name=employee.name, platform=assignment.platform)
