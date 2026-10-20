"""Completion threshold for the participation multiplier.

PRD §9.4 keeps "what an item earned" apart from "whether its owner took part":
participation becomes a multiplier on the personal score rather than a score
component of its own. This adds the threshold the multiplier is measured against.

Revision ID: 20261022_completion_threshold
Revises: 20261021_band_mapping
"""

import sqlalchemy as sa
from alembic import op

revision = "20261022_completion_threshold"
down_revision = "20261021_band_mapping"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assignments", sa.Column("completion_threshold", sa.Float(), nullable=False,
                                           server_default="0.9"))
    op.create_check_constraint("ck_assignments_completion_threshold", "assignments",
                               "completion_threshold > 0 AND completion_threshold <= 1")


def downgrade() -> None:
    op.drop_constraint("ck_assignments_completion_threshold", "assignments", type_="check")
    op.drop_column("assignments", "completion_threshold")
