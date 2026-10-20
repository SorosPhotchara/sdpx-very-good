"""Assignment lifecycle state and the events that move it.

PRD §7.3 gives an assignment an explicit state machine instead of inferring
everything from `published_at`, and requires a reason for unpublish and reopen.
FR-SCORE-09 requires finalize to snapshot both the inputs and the outputs of the
calculation, so a later formula change cannot rewrite a settled result.

Revision ID: 20261025_assignment_status
Revises: 20261024_pairing_policy
"""

import sqlalchemy as sa
from alembic import op

revision = "20261025_assignment_status"
down_revision = "20261024_pairing_policy"
branch_labels = None
depends_on = None

STATES = ("DRAFT", "PUBLISHED", "FINALIZED", "ARCHIVED")


def upgrade() -> None:
    op.add_column("assignments", sa.Column("status", sa.String(), nullable=False,
                                           server_default="DRAFT"))
    op.add_column("assignments", sa.Column("finalized_at", sa.DateTime(timezone=True),
                                           nullable=True))
    states = ", ".join(f"'{state}'" for state in STATES)
    op.create_check_constraint("ck_assignments_status", "assignments",
                               f"status IN ({states})")

    # Anything already published keeps that state; everything else is a draft.
    assignments = sa.table("assignments", sa.column("id", sa.Integer()),
                           sa.column("status", sa.String()),
                           sa.column("published_at", sa.DateTime(timezone=True)))
    op.get_bind().execute(
        assignments.update().where(assignments.c.published_at.is_not(None))
        .values(status="PUBLISHED"))

    op.create_table(
        "assignment_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assignments.id"),
                  nullable=False, index=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("actor_email", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        # Set for finalize only: the report that was settled, inputs and outputs
        # together, so it can be read back without recomputing it (FR-SCORE-09).
        sa.Column("snapshot", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("assignment_events")
    op.drop_constraint("ck_assignments_status", "assignments", type_="check")
    op.drop_column("assignments", "finalized_at")
    op.drop_column("assignments", "status")
