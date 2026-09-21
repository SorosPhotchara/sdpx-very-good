"""Track student activation and assignment publication explicitly.

Revision ID: 20260920_lifecycle
Revises: 20260919_reassignments
"""

import sqlalchemy as sa
from alembic import op

revision = "20260920_lifecycle"
down_revision = "20260919_reassignments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("students") as batch_op:
        batch_op.add_column(sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.add_column(sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    connection = op.get_bind()
    assignments = sa.table("assignments", sa.column("id", sa.Integer()), sa.column("published_at", sa.DateTime(timezone=True)))
    pairs = sa.table("pairs", sa.column("assignment_id", sa.Integer()))
    connection.execute(
        assignments.update().where(assignments.c.id.in_(sa.select(pairs.c.assignment_id)))
        .values(published_at=sa.func.current_timestamp())
    )


def downgrade() -> None:
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.drop_column("published_at")
    with op.batch_alter_table("students") as batch_op:
        batch_op.drop_column("activated_at")
