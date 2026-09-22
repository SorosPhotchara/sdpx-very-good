"""Add separate evaluation deadlines and participation maxima.

Revision ID: 20260919_assignment_policy
Revises: 20260919_pair_evaluator
"""

import sqlalchemy as sa
from alembic import op

revision = "20260919_assignment_policy"
down_revision = "20260919_pair_evaluator"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.add_column(sa.Column("group_participation_max", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("individual_participation_max", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("group_deadline", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("individual_deadline", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.drop_column("individual_deadline")
        batch_op.drop_column("group_deadline")
        batch_op.drop_column("individual_participation_max")
        batch_op.drop_column("group_participation_max")
