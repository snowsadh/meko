"""Durable Slack intake and per-company memory-routing checkpoints."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SlackChunk(Base):
    __tablename__ = "slack_chunks"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    channel_id: Mapped[str] = mapped_column(String(100))
    thread_ts: Mapped[str | None] = mapped_column(String(50))
    private: Mapped[bool] = mapped_column(default=False)
    messages: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    company: Mapped[bool] = mapped_column(default=False)
    employee_ids: Mapped[list] = mapped_column(JSONB, default=list)
    reason: Mapped[str | None] = mapped_column(Text)
    deliveries: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SlackMessage(Base):
    __tablename__ = "slack_messages"
    __table_args__ = (
        UniqueConstraint("org_id", "channel_id", "message_ts", name="uq_slack_source_message"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    channel_id: Mapped[str] = mapped_column(String(100))
    message_ts: Mapped[str] = mapped_column(String(50))
    thread_ts: Mapped[str | None] = mapped_column(String(50))
    channel_type: Mapped[str] = mapped_column(String(20))
    user_id: Mapped[str] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text)
    is_bot: Mapped[bool] = mapped_column(default=False)
    recipient_ids: Mapped[list] = mapped_column(JSONB, default=list)
    chunk_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("slack_chunks.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
