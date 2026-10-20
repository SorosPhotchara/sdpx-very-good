"""Per-assignment band mapping for quality index to score.

Replaces normalise-to-one with `floor + (ceiling - floor) * q` (PRD D2, §9.3),
so the band bounds become assignment configuration.

Revision ID: 20261021_band_mapping
Revises: 20261020_six_point_scale
"""

import sqlalchemy as sa
from alembic import op

revision = "20261021_band_mapping"
down_revision = "20261020_six_point_scale"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assignments", sa.Column("score_floor", sa.Float(), nullable=False,
                                           server_default="0.6"))
    op.add_column("assignments", sa.Column("score_ceiling", sa.Float(), nullable=False,
                                           server_default="1.0"))
    op.create_check_constraint("ck_assignments_score_band", "assignments",
                               "score_floor >= 0 AND score_ceiling <= 1 "
                               "AND score_floor < score_ceiling")


def downgrade() -> None:
    op.drop_constraint("ck_assignments_score_band", "assignments", type_="check")
    op.drop_column("assignments", "score_ceiling")
    op.drop_column("assignments", "score_floor")
