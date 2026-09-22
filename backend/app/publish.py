"""Build and persist pair assignments for an instructor assignment."""

from dataclasses import dataclass
from datetime import UTC, datetime
from math import isclose

from sqlalchemy.orm import Session

from . import models
from .pairing import PairAllocation, allocate_group_pairs, allocate_individual_pairs


@dataclass(frozen=True)
class PlannedPair:
    criterion_id: int
    allocation: PairAllocation


def build_plan(db: Session, assignment_id: int) -> list[PlannedPair]:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise ValueError("Assignment not found")

    groups = db.query(models.Group).filter_by(classroom_id=assignment.classroom_id).all()
    active = {group.id: [student.id for student in group.students] for group in groups if group.students}
    if len(active) < 3:
        raise ValueError("At least three non-empty groups are required")

    criteria = db.query(models.Criteria).filter_by(assignment_id=assignment_id).all()
    if not criteria:
        raise ValueError("Assignment has no criteria")
    for is_group, maximum in (
        (True, (assignment.group_score or 0) + (assignment.group_participation_max or 0)),
        (False, (assignment.individual_score or 0) + (assignment.individual_participation_max or 0)),
    ):
        selected = [criterion for criterion in criteria if criterion.is_group == is_group]
        deadline = assignment.group_deadline if is_group else assignment.individual_deadline
        if deadline is not None and deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)
        if selected and (deadline is None or deadline <= datetime.now(UTC)):
            raise ValueError("Cannot publish a section without a future deadline")
        if maximum and not selected:
            raise ValueError("A scored section needs at least one criterion")
        if selected and (not maximum or not isclose(sum(item.weight for item in selected), 100.0, abs_tol=0.001)):
            raise ValueError("Criterion weights must total 100 percent in each scored section")

    plan: list[PlannedPair] = []
    for criterion in criteria:
        if criterion.is_group:
            allocations = allocate_group_pairs(active, seed=criterion.id)
        else:
            allocations = [
                allocation
                for group_id, members in active.items()
                for allocation in allocate_individual_pairs(members, seed=criterion.id * 1_000_003 + group_id)
            ]
        plan.extend(PlannedPair(criterion.id, allocation) for allocation in allocations)
    return plan


def publish(db: Session, assignment_id: int) -> int:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise ValueError("Assignment not found")
    if assignment.published_at is not None or db.query(models.Pair.id).filter_by(assignment_id=assignment_id).first():
        raise ValueError("Assignment is already published")
    plan = build_plan(db, assignment_id)
    if not plan:
        raise ValueError("No eligible pairs can be published")
    pairs = []
    for item in plan:
        allocation = item.allocation
        pairs.append(models.Pair(
            assignment_id=assignment_id,
            criteria_id=item.criterion_id,
            pair_type=allocation.kind,
            left_group_id=allocation.left_id if allocation.kind == "group" else None,
            right_group_id=allocation.right_id if allocation.kind == "group" else None,
            left_id=allocation.left_id if allocation.kind == "individual" else None,
            right_id=allocation.right_id if allocation.kind == "individual" else None,
            assigned_to_student_id=allocation.evaluator_id,
        ))
    try:
        assignment.published_at = datetime.now(UTC)
        db.add_all(pairs)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return len(pairs)
