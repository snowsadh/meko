"""Company and employee context, Meko documents, and visible agent runs."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "7a8b9c0d1e2f"
down_revision = "3b1c2d4e5f6a"
branch_labels = None
depends_on = None


def upgrade():
    for table in ["organizations", "employees"]:
        op.add_column(table, sa.Column("meko_datapack_id", sa.String(36)))
        op.add_column(table, sa.Column("memory_setup_error", sa.Text()))
        op.create_unique_constraint(f"uq_{table}_meko_datapack", table, ["meko_datapack_id"])
    op.add_column("employees", sa.Column("context_version", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("employees", sa.Column("custom_instructions", sa.Text()))
    op.add_column("employees", sa.Column("auto_memory", sa.Boolean(), nullable=False, server_default=sa.true()))
    for column in [
        sa.Column("content_bytes", sa.LargeBinary()), sa.Column("content_type", sa.String(255)),
        sa.Column("size_bytes", sa.Integer()), sa.Column("content_hash", sa.String(64)),
        sa.Column("meko_datapack_id", sa.String(36)), sa.Column("meko_document_key", sa.String(2048)),
        sa.Column("meko_document_id", sa.String(36)), sa.Column("origin_memory_id", sa.String(36)),
        sa.Column("origin_employee_id", sa.Uuid(), sa.ForeignKey("employees.id", ondelete="SET NULL")),
    ]:
        op.add_column("memory_sources", column)
    for name in ["source_type", "exactly_one_content", "type_content"]:
        op.drop_constraint(f"ck_memory_sources_{name}", "memory_sources", type_="check")
    op.create_check_constraint("ck_memory_sources_source_type", "memory_sources", "source_type IN ('text','url','file')")
    op.create_check_constraint("ck_memory_sources_exactly_one_content", "memory_sources",
        "(content_text IS NOT NULL AND source_url IS NULL) OR "
        "(content_text IS NULL AND source_url IS NOT NULL) OR "
        "(content_bytes IS NOT NULL AND content_text IS NULL AND source_url IS NULL)")
    op.create_check_constraint("ck_memory_sources_type_content", "memory_sources",
        "(source_type='text' AND content_text IS NOT NULL) OR "
        "(source_type='url' AND source_url IS NOT NULL) OR (source_type='file' AND content_bytes IS NOT NULL)")
    op.create_table("agent_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.Uuid(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_key", sa.String(255), nullable=False, unique=True),
        sa.Column("thread_key", sa.String(255), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("input", sa.Text(), nullable=False), sa.Column("output", sa.Text()),
        sa.Column("recalled", postgresql.JSONB(), nullable=False),
        sa.Column("tools", postgresql.JSONB(), nullable=False),
        sa.Column("meko_conversation_id", sa.String(100)),
        sa.Column("context_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delivery_status", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("capture_status", sa.String(20), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for name in ["org_id", "employee_id", "thread_key"]:
        op.create_index(f"ix_agent_runs_{name}", "agent_runs", [name])


def downgrade():
    if op.get_bind().execute(sa.text("SELECT count(*) FROM memory_sources WHERE source_type='file'")).scalar():
        raise RuntimeError("Export/remove Meko file sources before downgrading this schema.")
    for name in ["source_type", "exactly_one_content", "type_content"]:
        op.drop_constraint(f"ck_memory_sources_{name}", "memory_sources", type_="check")
    op.create_check_constraint("ck_memory_sources_source_type", "memory_sources", "source_type IN ('text','url')")
    op.create_check_constraint("ck_memory_sources_exactly_one_content", "memory_sources",
        "(content_text IS NOT NULL AND source_url IS NULL) OR (content_text IS NULL AND source_url IS NOT NULL)")
    op.create_check_constraint("ck_memory_sources_type_content", "memory_sources",
        "(source_type='text' AND content_text IS NOT NULL) OR (source_type='url' AND source_url IS NOT NULL)")
    op.drop_table("agent_runs")
    for name in ["content_bytes", "content_type", "size_bytes", "content_hash", "meko_datapack_id",
                 "meko_document_key", "meko_document_id", "origin_memory_id", "origin_employee_id"]:
        op.drop_column("memory_sources", name)
    for name in ["custom_instructions", "auto_memory", "context_version"]:
        op.drop_column("employees", name)
    for table in ["organizations", "employees"]:
        op.drop_constraint(f"uq_{table}_meko_datapack", table, type_="unique")
        op.drop_column(table, "memory_setup_error")
        op.drop_column(table, "meko_datapack_id")
