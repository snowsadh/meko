from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.organizations.models import Organization
from app.organizations.schemas import CreateOrganizationRequest, UpdateOrganizationRequest


async def create_org(
    db: AsyncSession, user_id: UUID, data: CreateOrganizationRequest
) -> Organization:
    org = Organization(
        owner_id=user_id,
        name=data.name,
        description=data.description,
        what_it_does=data.what_it_does,
        website_url=data.website_url,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    from app.memory.scopes import connect_org
    return await connect_org(db, org)


async def get_org(db: AsyncSession, org_id: UUID, user_id: UUID) -> Organization | None:
    return await db.scalar(
        select(Organization)
        .options(selectinload(Organization.employees))
        .where(
            Organization.id == org_id, Organization.owner_id == user_id
        )
    )


async def list_orgs(db: AsyncSession, user_id: UUID) -> list[Organization]:
    result = await db.execute(
        select(Organization)
        .where(Organization.owner_id == user_id)
        .order_by(Organization.created_at.desc())
    )
    return list(result.scalars().all())


async def update_org(
    db: AsyncSession, org_id: UUID, user_id: UUID, data: UpdateOrganizationRequest
) -> Organization | None:
    org = await get_org(db, org_id, user_id)
    if org is None:
        return None
    if data.name is not None:
        org.name = data.name
    if data.description is not None:
        org.description = data.description
    if data.what_it_does is not None:
        org.what_it_does = data.what_it_does
    if data.website_url is not None:
        org.website_url = data.website_url
    await db.commit()
    await db.refresh(org)
    return org


async def delete_org(db: AsyncSession, org_id: UUID, user_id: UUID) -> bool:
    org = await get_org(db, org_id, user_id)
    if org is None:
        return False
    from app.core.meko import meko
    # Delete employee stores first. A failure retains the company record for retry.
    from app.employees.models import Employee
    employees = list((await db.scalars(select(Employee).where(Employee.org_id == org.id))).all())
    for emp in employees:
        if emp.meko_datapack_id:
            await meko.delete_pack(emp.meko_datapack_id)
            emp.meko_datapack_id = None
            await db.commit()
    if org.meko_datapack_id:
        await meko.delete_pack(org.meko_datapack_id)
    await db.delete(org)
    await db.commit()
    return True