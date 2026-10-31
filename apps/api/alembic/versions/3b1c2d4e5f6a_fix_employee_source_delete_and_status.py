"""Fix employee-scoped memory source deletion FK.

Revision ID: 3b1c2d4e5f6a
Revises: 14b660f47f4d
Create Date: 2026-07-11 00:35:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "3b1c2d4e5f6a"
down_revision: Union[str, Sequence[str], None] = "14b660f47f4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("memory_sources_employee_id_fkey", "memory_sources", type_="foreignkey")
    op.create_foreign_key(
        "memory_sources_employee_id_fkey",
        "memory_sources",
        "employees",
        ["employee_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("memory_sources_employee_id_fkey", "memory_sources", type_="foreignkey")
    op.create_foreign_key(
        "memory_sources_employee_id_fkey",
        "memory_sources",
        "employees",
        ["employee_id"],
        ["id"],
        ondelete="SET NULL",
    )
