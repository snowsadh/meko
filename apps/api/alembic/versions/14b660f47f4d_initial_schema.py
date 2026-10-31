"""Initial schema for a clean OpenHuman database.

Revision ID: 14b660f47f4d
Revises:
Create Date: 2026-07-10 15:33:12.937975
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "14b660f47f4d"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("clerk_id", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("onboarding_completed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clerk_id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_clerk_id"), "users", ["clerk_id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("what_it_does", sa.Text(), nullable=True),
        sa.Column("website_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organizations_owner_id"), "organizations", ["owner_id"], unique=False)

    op.create_table(
        "employees",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=True),
        sa.Column("personality", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("specialization", sa.String(length=255), nullable=True),
        sa.Column("employee_type", sa.String(length=50), nullable=True),
        sa.Column("duties", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("discord_token_enc", sa.Text(), nullable=True),
        sa.Column("slack_token_enc", sa.Text(), nullable=True),
        sa.Column("slack_team_id", sa.String(length=50), nullable=True),
        sa.Column("slack_team_name", sa.String(length=255), nullable=True),
        sa.Column("slack_bot_user_id", sa.String(length=50), nullable=True),
        sa.Column("memory_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("escalation_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="inactive", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'inactive', 'suspended')", name="ck_employees_status"),
        sa.CheckConstraint(
            "employee_type IS NULL OR employee_type IN ('legal-compliance', 'support', 'hr', 'general', 'sales')",
            name="ck_employees_employee_type",
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_employees_org_id"), "employees", ["org_id"], unique=False)
    op.create_index(
        "ix_employees_org_id_employee_type",
        "employees",
        ["org_id", "employee_type"],
        unique=True,
        postgresql_where=sa.text("employee_type IS NOT NULL"),
    )

    op.create_table(
        "channel_assignments",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("channel_name", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "employee_id",
            "platform",
            "channel_id",
            name="uq_channel_assignments_employee_platform_channel",
        ),
    )
    op.create_index(op.f("ix_channel_assignments_employee_id"), "channel_assignments", ["employee_id"], unique=False)

    op.create_table(
        "activity_events",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("employee_id", sa.Uuid(), nullable=True),
        sa.Column("employee_name", sa.String(length=255), nullable=True),
        sa.Column("platform", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activity_events_employee_id"), "activity_events", ["employee_id"], unique=False)
    op.create_index(op.f("ix_activity_events_event_type"), "activity_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_activity_events_occurred_at"), "activity_events", ["occurred_at"], unique=False)
    op.create_index(op.f("ix_activity_events_org_id"), "activity_events", ["org_id"], unique=False)
    op.create_index("ix_activity_events_org_occurred", "activity_events", ["org_id", "occurred_at"], unique=False)

    op.create_table(
        "agent_jobs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("channel_id", sa.String(length=255), nullable=False),
        sa.Column("thread_key", sa.String(length=500), nullable=False),
        sa.Column("job_type", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("user_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("result_text", sa.Text(), nullable=True),
        sa.Column("progress", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','running','awaiting_approval','succeeded','failed','cancelled')",
            name="ck_agent_jobs_status",
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_jobs_employee_id"), "agent_jobs", ["employee_id"], unique=False)
    op.create_index(op.f("ix_agent_jobs_job_type"), "agent_jobs", ["job_type"], unique=False)
    op.create_index(op.f("ix_agent_jobs_status"), "agent_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_agent_jobs_thread_key"), "agent_jobs", ["thread_key"], unique=False)

    op.create_table(
        "mcp_connections",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=True),
        sa.Column("connector_slug", sa.String(length=100), nullable=False),
        sa.Column("auth_type", sa.String(length=50), nullable=False),
        sa.Column("credentials_enc", sa.Text(), nullable=True),
        sa.Column("server_url", sa.String(length=1000), nullable=True),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="connected", nullable=False),
        sa.Column("connected_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connected_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mcp_connections_employee_id"), "mcp_connections", ["employee_id"], unique=False)
    op.create_index(op.f("ix_mcp_connections_org_id"), "mcp_connections", ["org_id"], unique=False)

    op.create_table(
        "memory_sources",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=True),
        sa.Column("source_type", sa.String(length=10), nullable=False),
        sa.Column("scope", sa.String(length=10), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("provider_memory_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=10), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(scope = 'org' AND employee_id IS NULL) OR (scope = 'employee' AND employee_id IS NOT NULL)",
            name="ck_memory_sources_scope_employee",
        ),
        sa.CheckConstraint(
            "(source_type = 'text' AND content_text IS NOT NULL) OR (source_type = 'url' AND source_url IS NOT NULL)",
            name="ck_memory_sources_type_content",
        ),
        sa.CheckConstraint("scope IN ('org', 'employee')", name="ck_memory_sources_scope"),
        sa.CheckConstraint("source_type IN ('text', 'url')", name="ck_memory_sources_source_type"),
        sa.CheckConstraint("status IN ('pending', 'indexed', 'failed')", name="ck_memory_sources_status"),
        sa.CheckConstraint(
            "(content_text IS NOT NULL AND source_url IS NULL) OR (content_text IS NULL AND source_url IS NOT NULL)",
            name="ck_memory_sources_exactly_one_content",
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_memory_sources_employee_id"), "memory_sources", ["employee_id"], unique=False)
    op.create_index(op.f("ix_memory_sources_org_id"), "memory_sources", ["org_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_memory_sources_org_id"), table_name="memory_sources")
    op.drop_index(op.f("ix_memory_sources_employee_id"), table_name="memory_sources")
    op.drop_table("memory_sources")

    op.drop_index(op.f("ix_mcp_connections_org_id"), table_name="mcp_connections")
    op.drop_index(op.f("ix_mcp_connections_employee_id"), table_name="mcp_connections")
    op.drop_table("mcp_connections")

    op.drop_index(op.f("ix_agent_jobs_thread_key"), table_name="agent_jobs")
    op.drop_index(op.f("ix_agent_jobs_status"), table_name="agent_jobs")
    op.drop_index(op.f("ix_agent_jobs_job_type"), table_name="agent_jobs")
    op.drop_index(op.f("ix_agent_jobs_employee_id"), table_name="agent_jobs")
    op.drop_table("agent_jobs")

    op.drop_index("ix_activity_events_org_occurred", table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_org_id"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_occurred_at"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_event_type"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_employee_id"), table_name="activity_events")
    op.drop_table("activity_events")

    op.drop_index(op.f("ix_channel_assignments_employee_id"), table_name="channel_assignments")
    op.drop_table("channel_assignments")

    op.drop_index("ix_employees_org_id_employee_type", table_name="employees")
    op.drop_index(op.f("ix_employees_org_id"), table_name="employees")
    op.drop_table("employees")

    op.drop_index(op.f("ix_organizations_owner_id"), table_name="organizations")
    op.drop_table("organizations")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_clerk_id"), table_name="users")
    op.drop_table("users")
