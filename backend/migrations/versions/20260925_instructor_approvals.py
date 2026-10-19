"""Store administrator-approved instructor accounts in PostgreSQL.

Revision ID: 20260925_instructor_approvals
Revises: 20260920_lifecycle
"""

import sqlalchemy as sa
from alembic import op

revision = "20260925_instructor_approvals"
down_revision = "20260920_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "instructor_approvals",
        sa.Column("email", sa.String(), primary_key=True),
        sa.Column("approved_by", sa.String(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("instructor_approvals")
