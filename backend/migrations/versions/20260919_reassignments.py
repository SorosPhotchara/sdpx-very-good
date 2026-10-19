"""Record group changes and superseded pair assignments.

Revision ID: 20260919_reassignments
Revises: 20260919_instructor_votes
"""

import sqlalchemy as sa
from alembic import op

revision = "20260919_reassignments"
down_revision = "20260919_instructor_votes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("pairs") as batch_op:
        batch_op.add_column(sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "reassignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("classroom_id", sa.Integer(), sa.ForeignKey("classrooms.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("old_group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("new_group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("instructor_email", sa.String(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("reassignments")
    with op.batch_alter_table("pairs") as batch_op:
        batch_op.drop_column("superseded_at")
