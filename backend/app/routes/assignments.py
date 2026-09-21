"""Assignments endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..assignment_setup import create_assignment as create_complete_assignment, update_assignment as update_complete_assignment
from ..auth import Identity, current_identity
from ..dependencies import get_db, instructor_emails, require_owner, utc_deadline, validate_page
from ..instructor_evaluation import assign_pair, read_instructor_pairs, save_instructor_vote
from ..publish import build_plan, publish

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
        query = query.filter(models.Assignment.published_at.is_not(None))
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
        group_participation_max=assignment.group_participation_max or 0,
        individual_participation_max=assignment.individual_participation_max or 0,
        instructor_weight=assignment.instructor_weight,
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


@router.get("/assignments/{assignment_id}/preview")
def preview_assignment(
    assignment_id: int,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    require_owner(assignment.classroom_id, identity, db)
    try:
        return {"pair_assignments": len(build_plan(db, assignment_id))}
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
