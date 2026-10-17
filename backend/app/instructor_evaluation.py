"""Targeted instructor pair assignments and weighted votes."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, schemas


def deadline_for(assignment: models.Assignment, is_group: bool):
    deadline = assignment.group_deadline if is_group else assignment.individual_deadline
    if deadline is not None and deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    return deadline


def _validate_pair(db: Session, assignment: models.Assignment, criteria_id: int,
                   left_id: int, right_id: int) -> tuple[models.Criteria, list]:
    if assignment.published_at is None:
        raise HTTPException(409, "Publish the assignment first")
    criterion = db.get(models.Criteria, criteria_id)
    if criterion is None or criterion.assignment_id != assignment.id:
        raise HTTPException(422, "Criterion is not in this assignment")
    deadline = deadline_for(assignment, criterion.is_group)
    if deadline is None or deadline <= datetime.now(UTC):
        raise HTTPException(409, "Evaluation deadline has passed")
    if left_id == right_id:
        raise HTTPException(422, "A pair needs two different items")
    model = models.Group if criterion.is_group else models.Student
    items = [db.get(model, item_id) for item_id in (left_id, right_id)]
    if any(item is None or item.classroom_id != assignment.classroom_id for item in items):
        raise HTTPException(422, "Both items must belong to the classroom")
    if criterion.is_group:
        if any(not item.students for item in items):
            raise HTTPException(422, "Groups must have members")
    else:
        if items[0].group_id is None or items[0].group_id != items[1].group_id:
            raise HTTPException(422, "Individual pair must be in one group")
        member_count = db.query(models.Student).filter_by(group_id=items[0].group_id).count()
        if member_count < 3:
            raise HTTPException(422, "Individual evaluation needs at least three group members")
    return criterion, items


def _ensure_new_evaluator_pair(db: Session, assignment: models.Assignment,
                               criterion: models.Criteria, left_id: int, right_id: int,
                               student_id: int | None = None, instructor_email: str | None = None) -> None:
    # Serialize manual assignments for this assignment; the database also enforces
    # uniqueness for active unordered pairs.
    db.query(models.Assignment).filter_by(id=assignment.id).with_for_update().one()
    query = db.query(models.Pair).filter_by(
        assignment_id=assignment.id, criteria_id=criterion.id, superseded_at=None,
    )
    if student_id is not None:
        query = query.filter(models.Pair.assigned_to_student_id == student_id)
    else:
        query = query.filter(func.lower(func.trim(models.Pair.assigned_to_instructor_email)) == instructor_email)
    existing = query.all()
    requested = {left_id, right_id}
    for pair in existing:
        current = ({pair.left_group_id, pair.right_group_id} if criterion.is_group
                   else {pair.left_id, pair.right_id})
        if current == requested:
            raise HTTPException(409, "Evaluator already has an active assignment for this pair")


def assign_pair(db: Session, assignment: models.Assignment, payload: schemas.InstructorPairRequest,
                instructor_emails: set[str]) -> models.Pair:
    email = str(payload.instructor_email).strip().lower()
    if email not in instructor_emails:
        raise HTTPException(422, "Instructor is not assigned to this classroom")
    criterion, _ = _validate_pair(db, assignment, payload.criteria_id, payload.left_id, payload.right_id)
    _ensure_new_evaluator_pair(db, assignment, criterion, payload.left_id, payload.right_id,
                               instructor_email=email)
    pair = models.Pair(
        assignment_id=assignment.id, criteria_id=criterion.id,
        pair_type="group" if criterion.is_group else "individual",
        left_group_id=payload.left_id if criterion.is_group else None,
        right_group_id=payload.right_id if criterion.is_group else None,
        left_id=payload.left_id if not criterion.is_group else None,
        right_id=payload.right_id if not criterion.is_group else None,
        assigned_to_instructor_email=email,
    )
    db.add(pair)
    db.commit()
    db.refresh(pair)
    return pair


def assign_student_pair(db: Session, assignment: models.Assignment,
                        payload: schemas.StudentPairRequest) -> models.Pair:
    criterion, items = _validate_pair(db, assignment, payload.criteria_id,
                                      payload.left_id, payload.right_id)
    student = db.get(models.Student, payload.student_id)
    if student is None or student.classroom_id != assignment.classroom_id or student.group_id is None:
        raise HTTPException(422, "Evaluator must belong to this classroom and a group")
    if criterion.is_group:
        if student.group_id in (items[0].id, items[1].id):
            raise HTTPException(422, "Evaluator cannot compare their own group")
    elif student.group_id != items[0].group_id or student.id in (items[0].id, items[1].id):
        raise HTTPException(422, "Individual evaluator must be another member of the same group")
    _ensure_new_evaluator_pair(db, assignment, criterion, items[0].id, items[1].id,
                               student_id=student.id)
    pair = models.Pair(
        assignment_id=assignment.id, criteria_id=criterion.id,
        pair_type="group" if criterion.is_group else "individual",
        left_group_id=items[0].id if criterion.is_group else None,
        right_group_id=items[1].id if criterion.is_group else None,
        left_id=items[0].id if not criterion.is_group else None,
        right_id=items[1].id if not criterion.is_group else None,
        assigned_to_student_id=student.id,
    )
    db.add(pair)
    db.commit()
    db.refresh(pair)
    return pair


def read_instructor_pairs(db: Session, assignment: models.Assignment, email: str) -> list[dict]:
    pairs = db.query(models.Pair).filter_by(assignment_id=assignment.id,
                                             assigned_to_instructor_email=email,
                                             superseded_at=None).order_by(models.Pair.id).all()
    votes = {vote.pair_id: vote for vote in db.query(models.InstructorVote).filter(
        models.InstructorVote.pair_id.in_([pair.id for pair in pairs]))}
    criteria = {item.id: item for item in assignment.criteria}
    result = []
    for pair in pairs:
        criterion = criteria[pair.criteria_id]
        model = models.Group if criterion.is_group else models.Student
        left = db.get(model, pair.left_group_id if criterion.is_group else pair.left_id)
        right = db.get(model, pair.right_group_id if criterion.is_group else pair.right_id)
        deadline = deadline_for(assignment, criterion.is_group)
        result.append({
            "pair_id": pair.id, "section": pair.pair_type, "criterion": criterion.name,
            "left": left.name if criterion.is_group else (left.display_name or left.email),
            "right": right.name if criterion.is_group else (right.display_name or right.email),
            "choice": votes[pair.id].choice if pair.id in votes else None,
            "is_open": deadline is not None and deadline > datetime.now(UTC),
        })
    return result


def save_instructor_vote(db: Session, assignment: models.Assignment, pair_id: int,
                         email: str, choice: int) -> dict:
    pair = db.get(models.Pair, pair_id)
    if pair is None or pair.assignment_id != assignment.id or pair.assigned_to_instructor_email != email or pair.superseded_at is not None:
        raise HTTPException(403, "Instructor pair not assigned")
    criterion = db.get(models.Criteria, pair.criteria_id)
    deadline = deadline_for(assignment, criterion.is_group)
    if deadline is None or deadline <= datetime.now(UTC):
        raise HTTPException(409, "Evaluation deadline has passed")
    vote = db.get(models.InstructorVote, pair.id)
    if vote is None:
        vote = models.InstructorVote(pair_id=pair.id)
        db.add(vote)
    vote.choice = choice
    vote.submitted_at = datetime.now(UTC)
    db.commit()
    return {"pair_id": pair.id, "choice": choice, "submitted_at": vote.submitted_at}
