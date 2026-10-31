from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, LargeBinary, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MemorySource(Base):
    __tablename__ = "memory_sources"
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('text', 'url', 'file')",
            name="ck_memory_sources_source_type",
        ),
        CheckConstraint(
            "scope IN ('org', 'employee')",
            name="ck_memory_sources_scope",
        ),
        CheckConstraint(
            "status IN ('pending', 'indexed', 'failed')",
            name="ck_memory_sources_status",
        ),
        CheckConstraint(
            "(content_text IS NOT NULL AND source_url IS NULL)"
            " OR (content_text IS NULL AND source_url IS NOT NULL)"
            " OR (content_bytes IS NOT NULL AND content_text IS NULL AND source_url IS NULL)",
            name="ck_memory_sources_exactly_one_content",
        ),
        CheckConstraint(
            "(scope = 'org' AND employee_id IS NULL)"
            " OR (scope = 'employee' AND employee_id IS NOT NULL)",
            name="ck_memory_sources_scope_employee",
        ),
        CheckConstraint(
            "(source_type = 'text' AND content_text IS NOT NULL)"
            " OR (source_type = 'url' AND source_url IS NOT NULL)"
            " OR (source_type = 'file' AND content_bytes IS NOT NULL)",
            name="ck_memory_sources_type_content",
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
    employee_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )
    scope: Mapped[str] = mapped_column(
        String(10), nullable=False
    )
    title: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    content_text: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    source_url: Mapped[str | None] = mapped_column(
        String(2048), nullable=True
    )
    provider_memory_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    content_bytes: Mapped[bytes | None] = mapped_column(LargeBinary)
    content_type: Mapped[str | None] = mapped_column(String(255))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    meko_datapack_id: Mapped[str | None] = mapped_column(String(36))
    meko_document_key: Mapped[str | None] = mapped_column(String(2048))
    meko_document_id: Mapped[str | None] = mapped_column(String(36))
    origin_memory_id: Mapped[str | None] = mapped_column(String(36))
    origin_employee_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(10), default="pending", server_default="pending"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), default=None, nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<MemorySource(id={self.id!r}, source_type={self.source_type!r}, "
            f"scope={self.scope!r}, status={self.status!r})>"
        )
