"""Persistence helpers around the pairing engine.

The pairing rules themselves live in :mod:`app.pairing` as pure functions, so
they can be property-tested without a database. This module only translates
between ORM rows and the engine's plain dataclasses.
"""

from __future__ import annotations

from typing import List, Sequence

from sqlalchemy.orm import Session

from . import models
from .domain import AssignmentConfig, Criterion, PairAssignment, Side, Student
from .pairing import generate_group_pairs, generate_individual_pairs


def _to_domain_students(rows: Sequence[models.Student]) -> list[Student]:
    """Adapt ORM rows to the engine's input type.

    ``group_id`` falls back to ``group_name`` because the CSV import records a
    name before the group row exists (FR-CLASS-04); students with neither are
    dropped, since an ungrouped student cannot be placed in any pair.
    """
    students: list[Student] = []
    for row in rows:
        group_key = row.group_id if row.group_id is not None else row.group_name
        if group_key is None:
            continue
        students.append(
            Student(
                id=str(row.id),
                email=row.email or "",
                display_name=row.display_name or "",
                group_id=str(group_key),
            )
        )
    return students


def _persist(
    db: Session,
    assignment_id: int,
    criteria_id: int,
    pairs: Sequence[PairAssignment],
    pair_type: str,
) -> int:
    for pair in pairs:
        row = models.Pair(
            assignment_id=assignment_id,
            criteria_id=criteria_id,
            pair_type=pair_type,
            evaluator_id=int(pair.evaluator_id),
            # FR-PAIR-08: store the position that was actually shown, or the
            # stored choice cannot be mapped back to an item later (§9.1).
            display_left_item_id=pair.display_left_item_id,
        )
        if pair_type == "group":
            row.left_group_id = int(pair.item_a_id)
            row.right_group_id = int(pair.item_b_id)
        else:
            row.left_id = int(pair.item_a_id)
            row.right_id = int(pair.item_b_id)
        db.add(row)
    db.commit()
    return len(pairs)


def create_group_pairs(
    db: Session,
    assignment_id: int,
    criteria_id: int,
    students: Sequence[models.Student],
    config: AssignmentConfig | None = None,
) -> int:
    """Generate and store group-vs-group pairs for one criterion.

    Takes students rather than group ids, because a pair is meaningless until
    it is attached to the evaluator who has to judge it (FR-PAIR-02).
    """
    config = config or AssignmentConfig()
    criterion = Criterion(
        id=str(criteria_id), side=Side.GROUP, name="", weight_pct=0
    )
    pairs = generate_group_pairs(
        _to_domain_students(students), criterion, config, str(assignment_id)
    )
    return _persist(db, assignment_id, criteria_id, pairs, "group")


def create_individual_pairs(
    db: Session,
    assignment_id: int,
    criteria_id: int,
    members: Sequence[models.Student],
    config: AssignmentConfig | None = None,
) -> int:
    """Generate and store within-group pairs for one criterion and one group."""
    config = config or AssignmentConfig()
    criterion = Criterion(
        id=str(criteria_id), side=Side.INDIVIDUAL, name="", weight_pct=0
    )
    pairs = generate_individual_pairs(
        _to_domain_students(members), criterion, config, str(assignment_id)
    )
    return _persist(db, assignment_id, criteria_id, pairs, "individual")


def generate_pairs(ids: List[int], target_coverage: int = 5):
    """Removed — it produced comparisons that nobody was assigned to judge.

    The old implementation emitted ``C(n,2) × coverage`` rows with no evaluator,
    no exclusion of an evaluator's own group (FR-PAIR-02/03), no feasibility
    check (§8.2), no duplicate guard (FR-PAIR-07) and no position randomisation
    (FR-PAIR-08). Use :func:`create_group_pairs` or
    :func:`create_individual_pairs` instead.
    """
    raise NotImplementedError(
        "generate_pairs() ถูกถอดออก เพราะไม่ผูก pair กับ evaluator — "
        "ใช้ create_group_pairs() หรือ create_individual_pairs() แทน"
    )
