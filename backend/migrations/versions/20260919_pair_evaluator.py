"""Store the evaluator assigned to each comparison.

Revision ID: 20260919_pair_evaluator
Revises: 20260919_student_membership
"""

import sqlalchemy as sa
from alembic import op

revision = "20260919_pair_evaluator"
down_revision = "20260919_student_membership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("pairs") as batch_op:
        batch_op.add_column(sa.Column("assigned_to_student_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_pairs_assigned_to_student_id_students",
            "students",
            ["assigned_to_student_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("pairs") as batch_op:
        batch_op.drop_constraint("fk_pairs_assigned_to_student_id_students", type_="foreignkey")
        batch_op.drop_column("assigned_to_student_id")
