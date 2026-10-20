"""Build and persist pair assignments for an instructor assignment."""

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from math import isclose

from sqlalchemy.orm import Session

from . import models
from .feasibility import Feasibility, solve_group_feasibility, solve_individual_feasibility
from .pairing import PairAllocation, allocate_group_pairs, allocate_individual_pairs


@dataclass(frozen=True)
class PlannedPair:
    criterion_id: int
    allocation: PairAllocation


def plan_feasibility(db: Session, assignment_id: int) -> dict:
    """The coverage and workload a publish would use, with the numbers behind it.

    FR-PAIR-04/05: an instructor sees this before publishing, including why a
    target was reduced, instead of discovering it from the coverage report after.
    """
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise ValueError("Assignment not found")
    groups = db.query(models.Group).filter_by(classroom_id=assignment.classroom_id).order_by(models.Group.id).all()
    sizes = {group.id: len(group.students) for group in groups if group.students}
    criteria = db.query(models.Criteria).filter_by(assignment_id=assignment_id).all()
    group_criteria = sum(1 for criterion in criteria if criterion.is_group)
    individual_criteria = len(criteria) - group_criteria

    group = solve_group_feasibility(list(sizes.values()), assignment.target_coverage,
                                    assignment.group_max_workload)
    individuals = {
        group_id: solve_individual_feasibility(size, assignment.individual_max_workload)
        for group_id, size in sizes.items()
    }
    return {
        "assignment_id": assignment_id,
        "students": sum(sizes.values()),
        "groups": len(sizes),
        "target_coverage": assignment.target_coverage,
        "group": {
            **_as_dict(group),
            "criteria": group_criteria,
            "comparisons_per_student": group.workload * group_criteria,
            "total_comparisons": group.comparisons * group_criteria,
        },
        "individual": {
            "criteria": individual_criteria,
            "total_comparisons": sum(item.comparisons for item in individuals.values()) * individual_criteria,
            "groups": [{"group_id": group_id, "members": sizes[group_id],
                        **_as_dict(item),
                        "comparisons_per_student": item.workload * individual_criteria}
                       for group_id, item in sorted(individuals.items())],
        },
    }


def _as_dict(item: Feasibility) -> dict:
    return {"coverage": item.coverage, "workload": item.workload, "pairs": item.pairs,
            "comparisons": item.comparisons, "requested": item.requested,
            "reduced": item.reduced, "feasible": item.feasible, "reason": item.reason}


def build_plan(db: Session, assignment_id: int) -> list[PlannedPair]:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise ValueError("Assignment not found")

    groups = db.query(models.Group).filter_by(classroom_id=assignment.classroom_id).order_by(models.Group.id).all()
    active = {group.id: sorted(student.id for student in group.students) for group in groups if group.students}
    if len(active) < 3:
        raise ValueError("At least three non-empty groups are required")

    criteria = db.query(models.Criteria).filter_by(assignment_id=assignment_id).order_by(models.Criteria.id).all()
    if not criteria:
        raise ValueError("Assignment has no criteria")
    for is_group, maximum in ((True, assignment.group_score or 0),
                              (False, assignment.individual_score or 0)):
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

    # §8.2/§8.3: settle coverage and workload before allocating anything, so the
    # plan matches what the instructor was shown by plan_feasibility.
    group_plan = solve_group_feasibility([len(members) for members in active.values()],
                                         assignment.target_coverage,
                                         assignment.group_max_workload)
    if not group_plan.feasible and any(criterion.is_group for criterion in criteria):
        raise ValueError(group_plan.reason or "Group evaluation is not feasible")
    base_seed = assignment.pairing_seed or 0

    plan: list[PlannedPair] = []
    group_loads: Counter[int] = Counter()
    individual_loads: Counter[int] = Counter()
    for criterion in criteria:
        if criterion.is_group:
            allocations = allocate_group_pairs(
                active, coverage=group_plan.coverage,
                seed=base_seed + criterion.id, initial_loads=group_loads,
                max_workload=assignment.group_max_workload,
            )
            group_loads.update(item.evaluator_id for item in allocations)
        else:
            allocations = []
            for group_id, members in active.items():
                individual_plan = solve_individual_feasibility(
                    len(members), assignment.individual_max_workload)
                if not individual_plan.feasible:
                    continue
                group_allocations = allocate_individual_pairs(
                    members, coverage=individual_plan.coverage,
                    seed=base_seed + criterion.id * 1_000_003 + group_id,
                    initial_loads=individual_loads,
                    max_workload=assignment.individual_max_workload,
                )
                allocations.extend(group_allocations)
                individual_loads.update(item.evaluator_id for item in group_allocations)
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
            display_flipped=allocation.flipped,
        ))
    try:
        assignment.published_at = datetime.now(UTC)
        db.add_all(pairs)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return len(pairs)
