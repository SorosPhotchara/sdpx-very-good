"""Create a complete assignment and its scoring criteria atomically."""

from datetime import UTC, datetime
from math import isclose

from sqlalchemy.orm import Session

from . import lifecycle, models, schemas
from .scoring import DEFAULT_COMPLETION_THRESHOLD, DEFAULT_SCORE_CEILING, DEFAULT_SCORE_FLOOR


def _validate_section(
    criteria: list[schemas.CriterionInput],
    score_max: float,
    deadline: datetime | None,
) -> bool:
    if score_max < 0:
        raise ValueError("Score maxima cannot be negative")
    active = score_max > 0
    if not active:
        if criteria:
            raise ValueError("Criteria need an active score section")
        return False
    if not criteria or not isclose(sum(item.weight for item in criteria), 100, abs_tol=0.001):
        raise ValueError("Criterion weights must total 100 percent")
    if any(not item.name.strip() or item.weight <= 0 for item in criteria):
        raise ValueError("Criteria need names and positive weights")
    names = [item.name.strip().casefold() for item in criteria]
    if len(names) != len(set(names)):
        raise ValueError("Criterion names must be distinct within a section")
    if deadline is None or deadline.tzinfo is None or deadline <= datetime.now(UTC):
        raise ValueError("Active sections need a future timezone-aware deadline")
    return True


def _pairing_policy(payload: schemas.AssignmentSetup) -> dict:
    """Only the pairing settings the caller actually supplied (§8.1)."""
    fields = ("target_coverage", "group_max_workload", "individual_max_workload",
              "min_comparisons")
    return {field: getattr(payload, field) for field in fields
            if getattr(payload, field) is not None}


def create_assignment(
    db: Session, classroom_id: int, payload: schemas.AssignmentSetup
) -> models.Assignment:
    if not payload.title.strip() or payload.instructor_weight <= 0:
        raise ValueError("Assignment title and instructor weight are required")
    group_active = _validate_section(
        payload.group_criteria, payload.group_score, payload.group_deadline,
    )
    individual_active = _validate_section(
        payload.individual_criteria, payload.individual_score, payload.individual_deadline,
    )
    if not group_active and not individual_active:
        raise ValueError("At least one evaluation section is required")

    assignment = models.Assignment(
        classroom_id=classroom_id,
        title=payload.title.strip(),
        group_score=payload.group_score,
        individual_score=payload.individual_score,
        instructor_weight=payload.instructor_weight,
        score_floor=DEFAULT_SCORE_FLOOR if payload.score_floor is None else payload.score_floor,
        score_ceiling=DEFAULT_SCORE_CEILING if payload.score_ceiling is None else payload.score_ceiling,
        completion_threshold=(DEFAULT_COMPLETION_THRESHOLD if payload.completion_threshold is None
                              else payload.completion_threshold),
        **_pairing_policy(payload),
        group_deadline=payload.group_deadline,
        individual_deadline=payload.individual_deadline,
    )
    try:
        db.add(assignment)
        db.flush()
        db.add_all([
            models.Criteria(
                assignment_id=assignment.id,
                name=criterion.name.strip(),
                weight=criterion.weight,
                is_group=is_group,
            )
            for is_group, criteria in ((True, payload.group_criteria), (False, payload.individual_criteria))
            for criterion in criteria
        ])
        db.commit()
        db.refresh(assignment)
    except Exception:
        db.rollback()
        raise
    return assignment


def update_assignment(db: Session, assignment: models.Assignment, payload: schemas.AssignmentSetup) -> models.Assignment:
    active_pairs = db.query(models.Pair.id).filter_by(
        assignment_id=assignment.id, superseded_at=None).first()
    if assignment.status != lifecycle.DRAFT or active_pairs:
        raise ValueError("Only draft assignments can be edited")
    if not payload.title.strip() or payload.instructor_weight <= 0:
        raise ValueError("Assignment title and instructor weight are required")
    group_active = _validate_section(payload.group_criteria, payload.group_score,
                                     payload.group_deadline)
    individual_active = _validate_section(payload.individual_criteria, payload.individual_score,
                                          payload.individual_deadline)
    if not group_active and not individual_active:
        raise ValueError("At least one evaluation section is required")
    assignment.title = payload.title.strip()
    assignment.group_score = payload.group_score
    assignment.individual_score = payload.individual_score
    assignment.instructor_weight = payload.instructor_weight
    if payload.score_floor is not None:
        assignment.score_floor = payload.score_floor
    if payload.score_ceiling is not None:
        assignment.score_ceiling = payload.score_ceiling
    if payload.completion_threshold is not None:
        assignment.completion_threshold = payload.completion_threshold
    for field, value in _pairing_policy(payload).items():
        setattr(assignment, field, value)
    assignment.group_deadline = payload.group_deadline
    assignment.individual_deadline = payload.individual_deadline
    try:
        db.query(models.Criteria).filter_by(assignment_id=assignment.id).delete()
        db.add_all([
            models.Criteria(assignment_id=assignment.id, name=criterion.name.strip(),
                            weight=criterion.weight, is_group=is_group)
            for is_group, criteria in ((True, payload.group_criteria), (False, payload.individual_criteria))
            for criterion in criteria
        ])
        db.commit()
        db.refresh(assignment)
    except Exception:
        db.rollback()
        raise
    return assignment
