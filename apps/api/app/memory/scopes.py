"""Company and employee ownership is checked before choosing a Meko scope."""

import re
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.meko import MekoError, meko, product_pack
from app.employees.models import Employee
from app.organizations.models import Organization


def employee_agent(employee_id: UUID) -> str:
    return f"openhuman:{employee_id}"


def datapack_name(company: str, employee: str | None = None) -> str:
    def slug(value):
        value = re.sub(r"[\W_]+", "-", value.casefold()).strip("-")
        if not value:
            raise MekoError("Company and employee names must contain letters or numbers.")
        return value

    company = slug(company)
    name = f"{company}-company-common" if employee is None else f"{slug(employee)}-{company}-emp"
    if len(name) > 60:
        raise MekoError("Shorten the company or employee name: datapack names allow 60 characters.")
    return name


async def owned_org(db: AsyncSession, org_id: UUID, user_id: UUID) -> Organization:
    org = await db.scalar(
        select(Organization).where(Organization.id == org_id, Organization.owner_id == user_id)
    )
    if org is None:
        raise HTTPException(404, "Company not found")
    return org


async def owned_employee(
    db: AsyncSession, org_id: UUID, employee_id: UUID, user_id: UUID
) -> tuple[Organization, Employee]:
    org = await owned_org(db, org_id, user_id)
    emp = await db.scalar(
        select(Employee).where(Employee.id == employee_id, Employee.org_id == org.id)
    )
    if emp is None:
        raise HTTPException(404, "Employee not found")
    return org, emp


async def connect_org(db: AsyncSession, org: Organization) -> Organization:
    if org.meko_datapack_id:
        product_pack(org.meko_datapack_id)
        return org
    try:
        org.meko_datapack_id = await meko.ensure_datapack(
            datapack_name(org.name), f"Shared knowledge for {org.name}. Company ID: {org.id}"
        )
        org.memory_setup_error = None
    except MekoError as exc:
        org.memory_setup_error = str(exc)
    await db.commit()
    return org


async def connect_employee(db: AsyncSession, org: Organization, emp: Employee) -> Employee:
    await connect_org(db, org)
    if emp.meko_datapack_id:
        product_pack(emp.meko_datapack_id)
        return emp
    try:
        if not org.meko_datapack_id:
            raise MekoError(org.memory_setup_error or "Company memory is not connected.")
        emp.meko_datapack_id = await meko.ensure_datapack(
            datapack_name(org.name, emp.name),
            f"Private working context for {emp.name}. Employee ID: {emp.id}",
        )
        emp.memory_setup_error = None
    except MekoError as exc:
        emp.memory_setup_error = str(exc)
    await db.commit()
    return emp


def require_pack(record: Organization | Employee) -> str:
    if not record.meko_datapack_id:
        raise MekoError(record.memory_setup_error or "Memory is not connected. Retry setup.")
    return product_pack(record.meko_datapack_id)
