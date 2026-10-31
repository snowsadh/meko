from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class McpConnection(Base):
    __tablename__ = "mcp_connections"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, server_default=func.gen_random_uuid())
    org_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    employee_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    connector_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    auth_type: Mapped[str] = mapped_column(String(50), nullable=False)
    credentials_enc: Mapped[str | None] = mapped_column(Text)
    server_url: Mapped[str | None] = mapped_column(String(1000))
    scopes: Mapped[list | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(50), default="connected", server_default="connected")
    connected_by_user_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
