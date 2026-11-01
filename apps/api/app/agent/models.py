from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    employee_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )
    request_key: Mapped[str] = mapped_column(String(255), unique=True)
    thread_key: Mapped[str] = mapped_column(String(255), index=True)
    platform: Mapped[str] = mapped_column(String(20), default="web")
    slack_channel_id: Mapped[str | None] = mapped_column(String(100))
    slack_thread_ts: Mapped[str | None] = mapped_column(String(50))
    input: Mapped[str] = mapped_column(Text)
    output: Mapped[str | None] = mapped_column(Text)
    recalled: Mapped[list] = mapped_column(JSONB, default=list)
    tools: Mapped[list] = mapped_column(JSONB, default=list)
    meko_conversation_id: Mapped[str | None] = mapped_column(String(100))
    context_version: Mapped[int] = mapped_column(default=0, server_default="0")
    delivery_status: Mapped[str] = mapped_column(String(20), default="not_applicable")
    status: Mapped[str] = mapped_column(String(20), default="running")
    capture_status: Mapped[str] = mapped_column(String(20), default="pending")
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentFile(Base):
    __tablename__ = "agent_files"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(180))
    media_type: Mapped[str] = mapped_column(String(120))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
