"""Store generated files with their originating employee run."""

import sqlalchemy as sa

from alembic import op

revision = "92b2c3d4e5f6"
down_revision = "6f09e54a2b10"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_files",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "run_id", sa.Uuid(), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("filename", sa.String(180), nullable=False),
        sa.Column("media_type", sa.String(120), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_agent_files_run_id", "agent_files", ["run_id"])


def downgrade():
    op.drop_table("agent_files")
