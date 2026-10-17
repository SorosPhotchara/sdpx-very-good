"""Keep one active evaluator assignment for each unordered pair.

Revision ID: 20261017_unique_pair_votes
Revises: 20261016_classroom_archives
"""

from collections import defaultdict
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "20261017_unique_pair_votes"
down_revision = "20261016_classroom_archives"
branch_labels = None
depends_on = None


def _instant(value: datetime | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _supersede_legacy_duplicates() -> None:
    connection = op.get_bind()
    pairs = sa.table(
        "pairs",
        sa.column("id", sa.Integer), sa.column("criteria_id", sa.Integer),
        sa.column("pair_type", sa.String), sa.column("left_id", sa.Integer),
        sa.column("right_id", sa.Integer), sa.column("left_group_id", sa.Integer),
        sa.column("right_group_id", sa.Integer), sa.column("assigned_to_student_id", sa.Integer),
        sa.column("assigned_to_instructor_email", sa.String),
        sa.column("superseded_at", sa.DateTime(timezone=True)),
    )
    submissions = sa.table(
        "submissions", sa.column("id", sa.Integer),
        sa.column("student_id", sa.Integer), sa.column("assignment_id", sa.Integer),
        sa.column("section", sa.String),
        sa.column("submitted_at", sa.DateTime(timezone=True)),
    )
    choices = sa.table(
        "submission_choices", sa.column("submission_id", sa.Integer),
        sa.column("pair_id", sa.Integer),
    )
    votes = sa.table(
        "instructor_votes", sa.column("pair_id", sa.Integer),
        sa.column("submitted_at", sa.DateTime(timezone=True)),
    )

    answered_at: dict[int, datetime] = {}
    latest_submissions = (sa.select(sa.func.max(submissions.c.id).label("id"))
                          .group_by(submissions.c.student_id, submissions.c.assignment_id,
                                    submissions.c.section).subquery())
    effective_choices = (choices.join(submissions, choices.c.submission_id == submissions.c.id)
                         .join(latest_submissions, submissions.c.id == latest_submissions.c.id))
    for pair_id, submitted_at in connection.execute(sa.select(
        choices.c.pair_id, submissions.c.submitted_at,
    ).select_from(effective_choices)):
        instant = _instant(submitted_at)
        if instant > answered_at.get(pair_id, datetime.min.replace(tzinfo=UTC)):
            answered_at[pair_id] = instant
    for pair_id, submitted_at in connection.execute(sa.select(votes.c.pair_id, votes.c.submitted_at)):
        instant = _instant(submitted_at)
        if instant > answered_at.get(pair_id, datetime.min.replace(tzinfo=UTC)):
            answered_at[pair_id] = instant

    duplicates: dict[tuple, list[int]] = defaultdict(list)
    for row in connection.execute(sa.select(pairs).where(pairs.c.superseded_at.is_(None))).mappings():
        if row["pair_type"] == "group":
            left, right = row["left_group_id"], row["right_group_id"]
        elif row["pair_type"] == "individual":
            left, right = row["left_id"], row["right_id"]
        else:
            continue
        if left is None or right is None:
            continue
        subjects = tuple(sorted((left, right)))
        prefix = (row["criteria_id"], row["pair_type"], *subjects)
        if row["assigned_to_student_id"] is not None:
            duplicates[(*prefix, "student", row["assigned_to_student_id"])].append(row["id"])
        if row["assigned_to_instructor_email"] is not None:
            normalized = row["assigned_to_instructor_email"].strip().lower()
            duplicates[(*prefix, "instructor", normalized)].append(row["id"])

    to_supersede: set[int] = set()
    for ids in duplicates.values():
        if len(ids) < 2:
            continue
        winner = max(ids, key=lambda pair_id: (
            pair_id in answered_at,
            answered_at.get(pair_id, datetime.min.replace(tzinfo=UTC)),
            pair_id,
        ))
        to_supersede.update(pair_id for pair_id in ids if pair_id != winner)
    if to_supersede:
        connection.execute(pairs.update().where(pairs.c.id.in_(sorted(to_supersede))).values(
            superseded_at=datetime.now(UTC),
        ))


def _index(name: str, evaluator: str, left: str, right: str, pair_type: str,
           present: str) -> None:
    lower = sa.text(f"(CASE WHEN {left} < {right} THEN {left} ELSE {right} END)")
    upper = sa.text(f"(CASE WHEN {left} < {right} THEN {right} ELSE {left} END)")
    condition = sa.text(f"superseded_at IS NULL AND pair_type = '{pair_type}' AND {present} IS NOT NULL")
    op.create_index(name, "pairs", ["criteria_id", sa.text(evaluator), lower, upper],
                    unique=True, postgresql_where=condition, sqlite_where=condition)


def upgrade() -> None:
    _supersede_legacy_duplicates()
    _index("uq_pairs_active_student_group", "assigned_to_student_id",
           "left_group_id", "right_group_id", "group", "assigned_to_student_id")
    _index("uq_pairs_active_student_individual", "assigned_to_student_id",
           "left_id", "right_id", "individual", "assigned_to_student_id")
    instructor = "lower(trim(assigned_to_instructor_email))"
    _index("uq_pairs_active_instructor_group", instructor,
           "left_group_id", "right_group_id", "group", "assigned_to_instructor_email")
    _index("uq_pairs_active_instructor_individual", instructor,
           "left_id", "right_id", "individual", "assigned_to_instructor_email")


def downgrade() -> None:
    # Keep superseded legacy rows historical; reviving them would double-count votes.
    for name in (
        "uq_pairs_active_student_group", "uq_pairs_active_student_individual",
        "uq_pairs_active_instructor_group", "uq_pairs_active_instructor_individual",
    ):
        op.drop_index(name, table_name="pairs")
