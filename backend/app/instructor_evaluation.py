"""Targeted instructor pair assignments and weighted votes."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import models, schemas


def deadline_for(assignment: models.Assignment, is_group: bool):
    deadline = assignment.group_deadline if is_group else assignment.individual_deadline
    if deadline is not None and deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    return deadline


def assign_pair(db: Session, assignment: models.Assignment, payload: schemas.InstructorPairRequest,
                instructor_emails: set[str]) -> models.Pair:
    if assignment.published_at is None:
        raise HTTPException(409, "Publish the assignment first")
    email = str(payload.instructor_email).strip().lower()
    if email not in instructor_emails:
        raise HTTPException(422, "Instructor is not assigned to this classroom")
    criterion = db.get(models.Criteria, payload.criteria_id)
    if criterion is None or criterion.assignment_id != assignment.id:
        raise HTTPException(422, "Criterion is not in this assignment")
    deadline = deadline_for(assignment, criterion.is_group)
    if deadline is None or deadline <= datetime.now(UTC):
        raise HTTPException(409, "Evaluation deadline has passed")
    if payload.left_id == payload.right_id:
        raise HTTPException(422, "A pair needs two different items")
    model = models.Group if criterion.is_group else models.Student
    items = [db.get(model, item_id) for item_id in (payload.left_id, payload.right_id)]
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
