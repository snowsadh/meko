from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.channel_assignments.schemas import ChannelAssignmentResponse
from app.core.security import decrypt_token, encrypt_token
from app.core.meko import meko
from app.memory.scopes import connect_employee, require_pack
from app.employees.models import Employee
from app.employees.schemas import (
    CreateEmployeeRequest,
    EmployeeResponse,
    UpdateEmployeeRequest,
)
from app.organizations.models import Organization

logger = logging.getLogger(__name__)


class DuplicateEmployeeTypeError(Exception):
    """Raised when creating/updating an employee to a type already used by the org."""


async def _get_org(db: AsyncSession, org_id: UUID, user_id: UUID) -> Organization | None:
    return await db.scalar(
        select(Organization).where(
            Organization.id == org_id, Organization.owner_id == user_id
        )
    )


async def _get_employee_with_assignments(
    db: AsyncSession, emp_id: UUID, org_id: UUID
) -> Employee | None:
    return await db.scalar(
        select(Employee)
        .where(Employee.id == emp_id, Employee.org_id == org_id)
        .options(selectinload(Employee.channel_assignments))
    )


def _to_response(emp: Employee) -> EmployeeResponse:
    return EmployeeResponse(
        id=emp.id,
        org_id=emp.org_id,
        name=emp.name,
        employee_type=emp.employee_type,
        role=emp.role,
        personality=emp.personality,
        specialization=emp.specialization,
        duties=emp.duties,
        memory_policy=emp.memory_policy,
        custom_instructions=emp.custom_instructions,
        auto_memory=emp.auto_memory,
        meko_datapack_id=emp.meko_datapack_id,
        memory_setup_error=emp.memory_setup_error,
        escalation_policy=emp.escalation_policy,
        mcp_connections=None,
        status=emp.status,
        has_discord_token=emp.discord_token_enc is not None,
        has_slack_token=emp.slack_token_enc is not None,
        slack_team_name=emp.slack_team_name,
        slack_bot_user_id=emp.slack_bot_user_id,
        channel_assignments=[
            ChannelAssignmentResponse.model_validate(ca, from_attributes=True)
            for ca in (emp.channel_assignments or [])
        ],
        created_at=emp.created_at,
        updated_at=emp.updated_at,
    )


async def create_employee(
    db: AsyncSession, org_id: UUID, user_id: UUID, data: CreateEmployeeRequest
) -> EmployeeResponse | None:
    org = await _get_org(db, org_id, user_id)
    if org is None:
        return None

    if data.employee_type:
        existing = await db.scalar(
            select(Employee).where(
                Employee.org_id == org_id,
                Employee.employee_type == data.employee_type,
            )
        )
        if existing is not None:
            raise DuplicateEmployeeTypeError(
                f"An employee of type '{data.employee_type}' already exists in this organization."
            )

    from app.employees.templates import get_template
    template = get_template(data.employee_type)
    emp = Employee(
        org_id=org_id,
        name=data.name,
        role=data.role or template.role,
        personality=data.personality or template.default_personality,
        specialization=data.specialization or data.employee_type,
        employee_type=data.employee_type,
        duties=data.duties if data.duties is not None else template.suggested_duties,
        memory_policy=data.memory_policy,
        custom_instructions=data.custom_instructions,
        auto_memory=data.auto_memory,
        escalation_policy=data.escalation_policy,
    )
    db.add(emp)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if "ix_employees_org_id_employee_type" in str(exc):
            raise DuplicateEmployeeTypeError(
                f"An employee of type '{data.employee_type}' already exists in this organization."
            ) from exc
        raise

    await connect_employee(db, org, emp)
    emp = await _get_employee_with_assignments(db, emp.id, org_id)  # type: ignore[assignment]
    return _to_response(emp)  # type: ignore[arg-type]


async def get_employee(
    db: AsyncSession, org_id: UUID, emp_id: UUID, user_id: UUID
) -> EmployeeResponse | None:
    org = await _get_org(db, org_id, user_id)
    if org is None:
        return None
    emp = await _get_employee_with_assignments(db, emp_id, org_id)
    if emp is None:
        return None
    return _to_response(emp)


async def get_employee_model(
    db: AsyncSession, org_id: UUID, emp_id: UUID, user_id: UUID
) -> Employee | None:
    org = await _get_org(db, org_id, user_id)
    if org is None:
        return None
    return await db.scalar(
        select(Employee).where(Employee.id == emp_id, Employee.org_id == org_id)
    )


async def list_employees(
    db: AsyncSession, org_id: UUID, user_id: UUID
) -> list[EmployeeResponse] | None:
    org = await _get_org(db, org_id, user_id)
    if org is None:
        return None
    result = await db.execute(
        select(Employee)
        .where(Employee.org_id == org_id)
        .options(selectinload(Employee.channel_assignments))
        .order_by(Employee.created_at.desc())
    )
    return [_to_response(e) for e in result.scalars().all()]


_ALLOWED_STATUSES = {"active", "inactive", "suspended"}


async def update_employee(
    db: AsyncSession, org_id: UUID, emp_id: UUID, user_id: UUID, data: UpdateEmployeeRequest
) -> EmployeeResponse | None:
    org = await _get_org(db, org_id, user_id)
    if org is None:
        return None
    emp = await _get_employee_with_assignments(db, emp_id, org_id)
    if emp is None:
        return None

    if data.employee_type is not None and data.employee_type != emp.employee_type:
        existing = await db.scalar(
            select(Employee).where(
                Employee.org_id == org_id,
                Employee.employee_type == data.employee_type,
                Employee.id != emp_id,
            )
        )
        if existing is not None:
            raise DuplicateEmployeeTypeError(
                f"An employee of type '{data.employee_type}' already exists in this organization."
            )

    update_data = data.model_dump(exclude_none=True)
    for field, value in update_data.items():
        if field == "status" and value not in _ALLOWED_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(_ALLOWED_STATUSES)}"
            )
        setattr(emp, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if "ix_employees_org_id_employee_type" in str(exc):
            raise DuplicateEmployeeTypeError(
                f"An employee of type '{data.employee_type}' already exists in this organization."
            ) from exc
        raise

    emp = await _get_employee_with_assignments(db, emp_id, org_id)  # type: ignore[assignment]
    return _to_response(emp)  # type: ignore[arg-type]


async def delete_employee(
    db: AsyncSession, org_id: UUID, emp_id: UUID, user_id: UUID
) -> bool:
    org = await _get_org(db, org_id, user_id)
    if org is None:
        return False
    emp = await db.scalar(
        select(Employee).where(Employee.id == emp_id, Employee.org_id == org_id)
    )
    if emp is None:
        return False

    if emp.meko_datapack_id:
        await meko.delete_pack(emp.meko_datapack_id)
    # Shared company lessons remain attributable and are not deleted with an employee.
    await db.delete(emp)
    await db.commit()
    return True


async def store_discord_token(
    db: AsyncSession, org_id: UUID, emp_id: UUID, user_id: UUID, token: str
) -> EmployeeResponse | None:
    org = await _get_org(db, org_id, user_id)
    if org is None:
        return None
    emp = await _get_employee_with_assignments(db, emp_id, org_id)
    if emp is None:
        return None
    emp.discord_token_enc = encrypt_token(token)
    await db.commit()
    emp = await _get_employee_with_assignments(db, emp_id, org_id)  # type: ignore[assignment]
    return _to_response(emp)  # type: ignore[arg-type]


async def store_slack_token(
    db: AsyncSession, org_id: UUID, emp_id: UUID, user_id: UUID, token: str
) -> EmployeeResponse | None:
    org = await _get_org(db, org_id, user_id)
    if org is None:
        return None
    emp = await _get_employee_with_assignments(db, emp_id, org_id)
    if emp is None:
        return None
    emp.slack_token_enc = encrypt_token(token)
    await db.commit()
    emp = await _get_employee_with_assignments(db, emp_id, org_id)  # type: ignore[assignment]
    return _to_response(emp)  # type: ignore[arg-type]


async def update_status(
    db: AsyncSession, org_id: UUID, emp_id: UUID, user_id: UUID, new_status: str
) -> EmployeeResponse | None:
    org = await _get_org(db, org_id, user_id)
    if org is None:
        return None
    emp = await _get_employee_with_assignments(db, emp_id, org_id)
    if emp is None:
        return None
    emp.status = new_status
    await db.commit()
    emp = await _get_employee_with_assignments(db, emp_id, org_id)  # type: ignore[assignment]
    return _to_response(emp)  # type: ignore[arg-type]


async def get_employee_raw(
    db: AsyncSession, emp_id: UUID
) -> Employee | None:
    return await db.scalar(select(Employee).where(Employee.id == emp_id))


async def get_active_employees_with_tokens(db: AsyncSession) -> list[Employee]:
    result = await db.execute(
        select(Employee)
        .where(
            Employee.status == "active",
            (Employee.discord_token_enc.is_not(None)) | (Employee.slack_token_enc.is_not(None)),
        )
    )
    return list(result.scalars().all())


def decrypt_discord_token(emp: Employee) -> str | None:
    if emp.discord_token_enc is None:
        return None
    return decrypt_token(emp.discord_token_enc)


def decrypt_slack_token(emp: Employee) -> str | None:
    if emp.slack_token_enc is None:
        return None
    return decrypt_token(emp.slack_token_enc)


async def get_employee_memory_profile(*args, **kwargs):
    from fastapi import HTTPException
    raise HTTPException(410, "Memory profiles are not a Meko feature. Browse the stored facts instead.")


async def get_employee_memory_explorer(db, org_id, emp_id, user_id, *, page=1, limit=25, query=None):
    from app.memory.scopes import owned_employee
    _, emp = await owned_employee(db, org_id, emp_id, user_id)
    result = await meko.list_memories(require_pack(emp), page=page, limit=limit, query=query)
    return {
        "memories": result.get("memories", []), "page": result.get("page", page),
        "total": result.get("total", 0), "total_pages": result.get("total_pages", 1),
    }
