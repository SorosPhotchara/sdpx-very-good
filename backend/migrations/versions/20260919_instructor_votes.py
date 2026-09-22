"""Add targeted instructor pair assignments and votes.

Revision ID: 20260919_instructor_votes
Revises: 20260919_evaluations
"""

import sqlalchemy as sa
from alembic import op

revision = "20260919_instructor_votes"
down_revision = "20260919_evaluations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("pairs") as batch_op:
        batch_op.add_column(sa.Column("assigned_to_instructor_email", sa.String(), nullable=True))
    op.create_table(
        "instructor_votes",
        sa.Column("pair_id", sa.Integer(), sa.ForeignKey("pairs.id"), primary_key=True),
        sa.Column("choice", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("instructor_votes")
    with op.batch_alter_table("pairs") as batch_op:
        batch_op.drop_column("assigned_to_instructor_email")
