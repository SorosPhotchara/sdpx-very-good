"""Six-point forced choice and randomised display order.

Adds the stored display order (FR-PAIR-08 / D8) and retires every answer that
was recorded on the five-point scale.

Revision ID: 20261020_six_point_scale
Revises: 20261017_unique_pair_votes
"""

import sqlalchemy as sa
from alembic import op

revision = "20261020_six_point_scale"
down_revision = "20261017_unique_pair_votes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pairs",
        sa.Column("display_flipped", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Every stored answer is on the retired five-point scale, where 3 meant
    # "equal" and 5 meant "right much better". Read against the six-point table
    # those same numbers mean 0.6/0.4 and 0.2/0.8, so keeping them would restate
    # what evaluators said instead of recording it. No faithful remapping exists
    # for 3 in particular, so the answers are removed and must be re-collected.
    # Children first: submission_choices references submissions.
    for table in ("submission_choices", "submissions", "draft_choices", "instructor_votes"):
        op.execute(sa.text(f"DELETE FROM {table}"))


def downgrade() -> None:
    op.drop_column("pairs", "display_flipped")
