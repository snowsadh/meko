"""Align inherited constraints, indexes, and comments with the imported models."""
from alembic import op

revision = "8b9c0d1e2f3a"
down_revision = "7a8b9c0d1e2f"
branch_labels = None
depends_on = None

COMMENTS = {
    "activity_events": {
        "description": "JSON string for expandable detail",
        "employee_name": "Denormalized for query speed",
        "platform": "slack | discord | api",
        "status": "succeeded | failed | pending | ...",
        "metadata": "Extra structured payload",
    },
    "agent_jobs": {
        "platform": "slack | discord",
        "thread_key": "Stable conversation id: {platform}:{employee_id}:{channel_id}:{root_ts}",
        "payload": "Tool arguments",
        "user_text": "Original user message text",
        "result_text": "Worker-written result",
        "progress": "Worker-updated progress blob",
    },
}


def employee_reference(ondelete):
    op.drop_constraint("activity_events_employee_id_fkey", "activity_events", type_="foreignkey")
    op.create_foreign_key("activity_events_employee_id_fkey", "activity_events", "employees",
                         ["employee_id"], ["id"], ondelete=ondelete)


def upgrade():
    employee_reference("SET NULL")
    for column in ("clerk_id", "email"):
        op.drop_constraint(f"users_{column}_key", "users", type_="unique")
        op.drop_index(f"ix_users_{column}", table_name="users")
        op.create_index(f"ix_users_{column}", "users", [column], unique=True)
    for table, columns in COMMENTS.items():
        for column, comment in columns.items():
            op.alter_column(table, column, comment=comment)


def downgrade():
    for table, columns in COMMENTS.items():
        for column in columns:
            op.alter_column(table, column, comment=None)
    for column in ("clerk_id", "email"):
        op.drop_index(f"ix_users_{column}", table_name="users")
        op.create_index(f"ix_users_{column}", "users", [column], unique=False)
        op.create_unique_constraint(f"users_{column}_key", "users", [column])
    employee_reference("CASCADE")
