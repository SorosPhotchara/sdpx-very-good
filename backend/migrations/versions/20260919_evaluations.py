"""Persist drafts and immutable submission snapshots.

Revision ID: 20260919_evaluations
Revises: 20260919_assignment_policy
"""

import sqlalchemy as sa
from alembic import op

revision = "20260919_evaluations"
down_revision = "20260919_assignment_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "draft_choices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("pair_id", sa.Integer(), sa.ForeignKey("pairs.id"), nullable=False),
        sa.Column("choice", sa.Integer(), nullable=False),
        sa.UniqueConstraint("student_id", "pair_id", name="uq_draft_student_pair"),
    )
    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id"), nullable=False),
        sa.Column("section", sa.String(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "submission_choices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("submission_id", sa.Integer(), sa.ForeignKey("submissions.id"), nullable=False),
        sa.Column("pair_id", sa.Integer(), sa.ForeignKey("pairs.id"), nullable=False),
        sa.Column("choice", sa.Integer(), nullable=False),
        sa.UniqueConstraint("submission_id", "pair_id", name="uq_submission_pair"),
    )


def downgrade() -> None:
    op.drop_table("submission_choices")
    op.drop_table("submissions")
    op.drop_table("draft_choices")
