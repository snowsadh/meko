from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.channel_assignments.models import ChannelAssignment
    from app.organizations.models import Organization


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        sa.Index("uq_employee_slack_identity", "slack_team_id", "slack_bot_user_id", unique=True),
        CheckConstraint(
            "status IN ('active', 'inactive', 'suspended')",
            name="ck_employees_status",
        ),
        CheckConstraint(
            "employee_type IS NULL OR employee_type IN ('legal-compliance', 'support', 'hr', 'general', 'sales')",
            name="ck_employees_employee_type",
        ),
        sa.Index(
            "ix_employees_org_id_employee_type",
            "org_id",
            "employee_type",
            unique=True,
            postgresql_where=sa.text("employee_type IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=func.gen_random_uuid()
    )
    org_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    personality: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employee_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duties: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    discord_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    slack_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)

    slack_team_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    slack_team_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    slack_bot_user_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    memory_policy: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    escalation_policy: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    custom_instructions: Mapped[str | None] = mapped_column(Text)
    meko_datapack_id: Mapped[str | None] = mapped_column(String(36), unique=True)
    memory_setup_error: Mapped[str | None] = mapped_column(Text)
    context_version: Mapped[int] = mapped_column(default=0, server_default="0")
    auto_memory: Mapped[bool] = mapped_column(default=True, server_default=sa.true())

    status: Mapped[str] = mapped_column(
        String(50), default="inactive", server_default="inactive"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), default=None, nullable=True
    )

    organization: Mapped[Organization] = relationship(
        "Organization", back_populates="employees"
    )
    channel_assignments: Mapped[list[ChannelAssignment]] = relationship(
        "ChannelAssignment",
        back_populates="employee",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
