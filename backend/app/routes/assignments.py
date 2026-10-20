"""Assignments endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..assignment_setup import create_assignment as create_complete_assignment, update_assignment as update_complete_assignment
from ..auth import Identity, current_identity
from ..dependencies import get_db, instructor_emails, require_owner, utc_deadline, validate_page
from ..instructor_evaluation import assign_pair, assign_student_pair, read_instructor_pairs, save_instructor_vote
from ..lifecycle import DRAFT, FINALIZED, PUBLISHED, move, record
from ..publish import build_plan, plan_feasibility, publish, withdraw
from ..reports import assignment_report

router = APIRouter(dependencies=[Depends(current_identity)])


@router.post("/classrooms/{classroom_id}/assignments", response_model=schemas.Assignment)
def create_assignment(
    classroom_id: int,
    payload: schemas.AssignmentSetup,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> models.Assignment:
    require_owner(classroom_id, identity, db)
    try:
        return create_complete_assignment(db, classroom_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/assignments/", response_model=list[schemas.Assignment])
def read_assignments(
    classroom_id: int,
    skip: int = 0,
    limit: int = 100,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> list[models.Assignment]:
    validate_page(skip, limit)
    member = db.query(models.Student.id).filter_by(classroom_id=classroom_id, email=identity.email).first()
    classroom = db.get(models.Classroom, classroom_id)
    is_owner = classroom is not None and identity.is_instructor and identity.email in instructor_emails(classroom)
    if member is None and not is_owner:
        require_owner(classroom_id, identity, db)
    query = db.query(models.Assignment).filter_by(classroom_id=classroom_id)
    if not is_owner:
        query = query.filter(models.Assignment.status != DRAFT)
    return query.offset(skip).limit(limit).all()


@router.get("/assignments/{assignment_id}/setup", response_model=schemas.AssignmentSetup)
def read_assignment_setup(
    assignment_id: int, identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> schemas.AssignmentSetup:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    require_owner(assignment.classroom_id, identity, db)
    return schemas.AssignmentSetup(
        title=assignment.title, group_score=assignment.group_score,
        individual_score=assignment.individual_score,
        instructor_weight=assignment.instructor_weight,
        score_floor=assignment.score_floor,
        score_ceiling=assignment.score_ceiling,
        completion_threshold=assignment.completion_threshold,
        target_coverage=assignment.target_coverage,
        group_max_workload=assignment.group_max_workload,
        individual_max_workload=assignment.individual_max_workload,
        min_comparisons=assignment.min_comparisons,
        group_deadline=utc_deadline(assignment.group_deadline),
        individual_deadline=utc_deadline(assignment.individual_deadline),
        group_criteria=[schemas.CriterionInput(name=item.name, weight=item.weight)
                        for item in assignment.criteria if item.is_group],
        individual_criteria=[schemas.CriterionInput(name=item.name, weight=item.weight)
                             for item in assignment.criteria if not item.is_group],
    )


@router.get("/assignments/{assignment_id}/criteria", response_model=list[schemas.Criteria])
def read_assignment_criteria(
    assignment_id: int, identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> list[models.Criteria]:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    require_owner(assignment.classroom_id, identity, db)
    return db.query(models.Criteria).filter_by(assignment_id=assignment_id).order_by(models.Criteria.id).all()


@router.put("/assignments/{assignment_id}/setup", response_model=schemas.Assignment)
def edit_assignment_setup(
    assignment_id: int, payload: schemas.AssignmentSetup,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> models.Assignment:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    require_owner(assignment.classroom_id, identity, db)
    try:
        return update_complete_assignment(db, assignment, payload)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


def _owned_assignment(assignment_id: int, identity: Identity, db: Session) -> models.Assignment:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    require_owner(assignment.classroom_id, identity, db)
    return assignment


@router.post("/assignments/{assignment_id}/unpublish")
def unpublish_assignment(
    assignment_id: int,
    payload: schemas.LifecycleRequest,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> dict:
    """Return an assignment to DRAFT so its setup can be changed (§7.3).

    The pairs and every answer against them are removed, which is what makes the
    criteria editable again, but they are kept on the lifecycle event first so
    nothing collected is simply lost (see `withdraw`).
    """
    assignment = _owned_assignment(assignment_id, identity, db)
    try:
        event = move(db, assignment, DRAFT, "unpublish", identity.email, payload.reason)
        event.snapshot = withdraw(db, assignment_id)
        assignment.published_at = None
        db.commit()
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"assignment_id": assignment_id, "status": assignment.status,
            "withdrawn_pairs": len(event.snapshot["pairs"]),
            "withdrawn_answers": (len(event.snapshot["submission_choices"])
                                  + len(event.snapshot["instructor_votes"]))}


@router.post("/assignments/{assignment_id}/finalize")
def finalize_assignment(
    assignment_id: int,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> dict:
    """Settle the scores and snapshot the calculation (FR-SCORE-09)."""
    assignment = _owned_assignment(assignment_id, identity, db)
    try:
        report = assignment_report(db, assignment)
        event = move(db, assignment, FINALIZED, "finalize", identity.email, report=report)
        db.commit()
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"assignment_id": assignment_id, "status": assignment.status,
            "finalized_at": assignment.finalized_at, "event_id": event.id}


@router.post("/assignments/{assignment_id}/reopen")
def reopen_assignment(
    assignment_id: int,
    payload: schemas.LifecycleRequest,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> dict:
    """Undo a finalize so scores can change again; needs a reason (§7.3)."""
    assignment = _owned_assignment(assignment_id, identity, db)
    try:
        move(db, assignment, PUBLISHED, "reopen", identity.email, payload.reason)
        db.commit()
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"assignment_id": assignment_id, "status": assignment.status}


@router.post("/assignments/{assignment_id}/recompute")
def recompute_assignment(
    assignment_id: int,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> dict:
    """Recompute on demand (FR-SCORE-06).

    Scores are derived on read, so this exists to answer "are these current?"
    and to leave a record that someone asked. A settled assignment is served
    from its snapshot instead, so finalized numbers never move.
    """
    assignment = _owned_assignment(assignment_id, identity, db)
    if assignment.status == FINALIZED:
        raise HTTPException(status_code=409,
                            detail="A finalized assignment is served from its snapshot")
    record(db, assignment, "recompute", identity.email)
    report = assignment_report(db, assignment)
    db.commit()
    return report


@router.get("/assignments/{assignment_id}/events")
def read_assignment_events(
    assignment_id: int,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Lifecycle history, newest first. Snapshots are large, so only their
    presence is reported here."""
    _owned_assignment(assignment_id, identity, db)
    events = (db.query(models.AssignmentEvent).filter_by(assignment_id=assignment_id)
              .order_by(models.AssignmentEvent.id.desc()).all())
    return [{"id": event.id, "action": event.action, "actor": event.actor_email,
             "reason": event.reason, "occurred_at": utc_deadline(event.occurred_at),
             "has_snapshot": event.snapshot is not None} for event in events]


@router.get("/assignments/{assignment_id}/feasibility")
def read_assignment_feasibility(
    assignment_id: int,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> dict:
    """FR-PAIR-04/05: the coverage and workload a publish would use, in numbers.

    Cheaper than /preview, which allocates every pair, and it is the call that
    tells an instructor a target was reduced before they commit to it.
    """
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    require_owner(assignment.classroom_id, identity, db)
    try:
        return plan_feasibility(db, assignment_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/assignments/{assignment_id}/preview")
def preview_assignment(
    assignment_id: int,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> dict[str, int | list[dict[str, str]]]:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    require_owner(assignment.classroom_id, identity, db)
    try:
        plan = build_plan(db, assignment_id)
        criteria = {item.id: item for item in db.query(models.Criteria).filter_by(assignment_id=assignment_id)}
        groups = {item.id: item.name for item in db.query(models.Group).filter_by(classroom_id=assignment.classroom_id)}
        students = {item.id: item for item in db.query(models.Student).filter_by(classroom_id=assignment.classroom_id)}
        pairs = []
        for item in plan:
            allocation = item.allocation
            is_group = allocation.kind == "group"
            left_id = allocation.left_id
            right_id = allocation.right_id
            pairs.append({
                "section": allocation.kind,
                "criterion": criteria[item.criterion_id].name,
                "left": groups[left_id] if is_group else (students[left_id].display_name or students[left_id].email),
                "right": groups[right_id] if is_group else (students[right_id].display_name or students[right_id].email),
                "evaluator": students[allocation.evaluator_id].email,
            })
        return {"pair_assignments": len(pairs), "pairs": pairs}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/assignments/{assignment_id}/publish")
def publish_assignment(
    assignment_id: int,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    require_owner(assignment.classroom_id, identity, db)
    try:
        return {"pair_assignments": publish(db, assignment_id)}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/assignments/{assignment_id}/instructor-pairs")
def add_instructor_pair(
    assignment_id: int, payload: schemas.InstructorPairRequest,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> dict:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    classroom = require_owner(assignment.classroom_id, identity, db)
    pair = assign_pair(db, assignment, payload, instructor_emails(classroom))
    return {"pair_id": pair.id}


@router.post("/assignments/{assignment_id}/student-pairs")
def add_student_pair(
    assignment_id: int, payload: schemas.StudentPairRequest,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> dict:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    require_owner(assignment.classroom_id, identity, db)
    pair = assign_student_pair(db, assignment, payload)
    return {"pair_id": pair.id}


@router.get("/assignments/{assignment_id}/instructor-pairs")
def list_instructor_pairs(
    assignment_id: int, identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> list[dict]:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    require_owner(assignment.classroom_id, identity, db)
    return read_instructor_pairs(db, assignment, identity.email)


@router.put("/assignments/{assignment_id}/instructor-pairs/{pair_id}/vote")
def record_instructor_vote(
    assignment_id: int, pair_id: int, payload: schemas.InstructorVoteRequest,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> dict:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    require_owner(assignment.classroom_id, identity, db)
    return save_instructor_vote(db, assignment, pair_id, identity.email, payload.choice)
