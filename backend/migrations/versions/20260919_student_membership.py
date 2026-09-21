"""Allow the same student email in multiple classrooms.

Revision ID: 20260919_student_membership
Revises: 35c1a9705009
"""

from alembic import op

revision = "20260919_student_membership"
down_revision = "35c1a9705009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("students") as batch_op:
        batch_op.drop_index("ix_students_email")
        batch_op.create_index("ix_students_email", ["email"])
        batch_op.create_unique_constraint(
            "uq_students_classroom_email", ["classroom_id", "email"]
        )


def downgrade() -> None:
    with op.batch_alter_table("students") as batch_op:
        batch_op.drop_constraint("uq_students_classroom_email", type_="unique")
        batch_op.drop_index("ix_students_email")
        batch_op.create_index("ix_students_email", ["email"], unique=True)
