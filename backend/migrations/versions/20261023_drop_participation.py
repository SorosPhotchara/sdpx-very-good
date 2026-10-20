"""Remove the participation score components.

Participation is a multiplier on the personal score now (PRD §9.4, D5), not a
score component with its own maximum, so the two maxima have no meaning left.
The ratio behind the multiplier is derived from assigned and submitted pairs, so
nothing needs to be carried over.

Revision ID: 20261023_drop_participation
Revises: 20261022_completion_threshold
"""

import sqlalchemy as sa
from alembic import op

revision = "20261023_drop_participation"
down_revision = "20261022_completion_threshold"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("assignments", "group_participation_max")
    op.drop_column("assignments", "individual_participation_max")


def downgrade() -> None:
    op.add_column("assignments", sa.Column("group_participation_max", sa.Float(),
                                           nullable=True, server_default="0"))
    op.add_column("assignments", sa.Column("individual_participation_max", sa.Float(),
                                           nullable=True, server_default="0"))
