"""Give existing template defaults readable capitalization."""

from alembic import op

revision = "6f09e54a2b10"
down_revision = "5e98dfa8413f"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE employees
        SET specialization = CASE employee_type
            WHEN 'support' THEN 'Support'
            WHEN 'hr' THEN 'HR'
            WHEN 'sales' THEN 'Sales'
            WHEN 'general' THEN 'General'
            WHEN 'legal-compliance' THEN 'Legal Compliance'
        END
        WHERE specialization = employee_type
          AND employee_type IN ('support', 'hr', 'sales', 'general', 'legal-compliance')
    """)


def downgrade():
    # Existing defaults and later custom text cannot be distinguished after editing.
    pass
