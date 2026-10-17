"""Retain deleted classroom evaluation and audit evidence.

Revision ID: 20261016_classroom_archives
Revises: 20260925_instructor_approvals
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "20261016_classroom_archives"
down_revision = "20260925_instructor_approvals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "classroom_archives",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("classroom_id", sa.Integer(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retain_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_by", sa.String(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
    )
    op.create_index("ix_classroom_archives_classroom_id", "classroom_archives", ["classroom_id"])

    # Existing prototype rooms predate the strict instructor allowlist. Keep
    # their current owners and add the first configured instructor so that the
    # rooms stay reachable after the role change.
    classrooms = sa.table("classrooms", sa.column("id", sa.Integer()),
                          sa.column("name", sa.String()), sa.column("instructor_emails", sa.Text()))
    connection = op.get_bind()
    prototypes = connection.execute(sa.select(classrooms).where(
        classrooms.c.name.in_(("d", "AAA", "www", "ECC777"))
    )).mappings().all()
    if prototypes:
        first = next((email.strip().lower() for email in os.environ.get("INSTRUCTOR_EMAILS", "").split(",")
                      if email.strip()), None)
        if first is None:
            raise RuntimeError("Set INSTRUCTOR_EMAILS before migrating existing prototype classrooms")
        for classroom in prototypes:
            instructors = {email.strip().lower() for email in (classroom["instructor_emails"] or "").split(",")
                           if email.strip()}
            instructors.add(first)
            connection.execute(classrooms.update().where(classrooms.c.id == classroom["id"]).values(
                instructor_emails=",".join(sorted(instructors))
            ))


def downgrade() -> None:
    op.drop_index("ix_classroom_archives_classroom_id", table_name="classroom_archives")
    op.drop_table("classroom_archives")
