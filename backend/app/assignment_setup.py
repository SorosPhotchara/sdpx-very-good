"""Create a complete assignment and its scoring criteria atomically."""

from datetime import UTC, datetime
from math import isclose

from sqlalchemy.orm import Session

from . import models, schemas


def _validate_section(
    criteria: list[schemas.CriterionInput],
    score_max: float,
    participation_max: float,
    deadline: datetime | None,
) -> bool:
    if score_max < 0 or participation_max < 0:
        raise ValueError("Score maxima cannot be negative")
    active = score_max > 0 or participation_max > 0
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


def create_assignment(
    db: Session, classroom_id: int, payload: schemas.AssignmentSetup
) -> models.Assignment:
    if not payload.title.strip() or payload.instructor_weight <= 0:
        raise ValueError("Assignment title and instructor weight are required")
    group_active = _validate_section(
        payload.group_criteria, payload.group_score,
        payload.group_participation_max, payload.group_deadline,
    )
    individual_active = _validate_section(
        payload.individual_criteria, payload.individual_score,
        payload.individual_participation_max, payload.individual_deadline,
    )
    if not group_active and not individual_active:
        raise ValueError("At least one evaluation section is required")

    assignment = models.Assignment(
        classroom_id=classroom_id,
        title=payload.title.strip(),
        group_score=payload.group_score,
        individual_score=payload.individual_score,
        group_participation_max=payload.group_participation_max,
        individual_participation_max=payload.individual_participation_max,
        instructor_weight=payload.instructor_weight,
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
    if assignment.published_at is not None or db.query(models.Pair.id).filter_by(assignment_id=assignment.id).first():
        raise ValueError("Published assignments cannot be edited")
    if not payload.title.strip() or payload.instructor_weight <= 0:
        raise ValueError("Assignment title and instructor weight are required")
    group_active = _validate_section(payload.group_criteria, payload.group_score,
                                     payload.group_participation_max, payload.group_deadline)
    individual_active = _validate_section(payload.individual_criteria, payload.individual_score,
                                          payload.individual_participation_max, payload.individual_deadline)
    if not group_active and not individual_active:
        raise ValueError("At least one evaluation section is required")
    assignment.title = payload.title.strip()
    assignment.group_score = payload.group_score
    assignment.individual_score = payload.individual_score
    assignment.group_participation_max = payload.group_participation_max
    assignment.individual_participation_max = payload.individual_participation_max
    assignment.instructor_weight = payload.instructor_weight
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
