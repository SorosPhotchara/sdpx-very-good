"""Per-assignment pairing policy: coverage target, workload ceilings, seed.

Coverage and workload stop being constants in the pairing code and become
assignment configuration the feasibility solver reads (PRD §8.1, §8.2, §8.3).
The two workload ceilings are deliberately separate: one value would make
individual coverage fall as groups grow, contradicting D4 (see FR-PAIR-14).

Revision ID: 20261024_pairing_policy
Revises: 20261023_drop_participation
"""

import sqlalchemy as sa
from alembic import op

revision = "20261024_pairing_policy"
down_revision = "20261023_drop_participation"
branch_labels = None
depends_on = None

COLUMNS = (
    ("target_coverage", sa.Integer(), "5", "target_coverage BETWEEN 1 AND 20"),
    ("group_max_workload", sa.Integer(), "8", "group_max_workload BETWEEN 1 AND 30"),
    ("individual_max_workload", sa.Integer(), "21", "individual_max_workload BETWEEN 1 AND 100"),
    ("min_comparisons", sa.Integer(), "3", "min_comparisons >= 1"),
)


def upgrade() -> None:
    for name, kind, default, check in COLUMNS:
        op.add_column("assignments", sa.Column(name, kind, nullable=False,
                                               server_default=default))
        op.create_check_constraint(f"ck_assignments_{name}", "assignments", check)
    # Null means "derive the seed from the criterion", which is what publishing
    # did before this column existed; setting it makes a run reproducible.
    op.add_column("assignments", sa.Column("pairing_seed", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("assignments", "pairing_seed")
    for name, _, _, _ in reversed(COLUMNS):
        op.drop_constraint(f"ck_assignments_{name}", "assignments", type_="check")
        op.drop_column("assignments", name)
