"""Student evaluation access, drafts, and immutable submissions."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import models
from .timezone import as_utc


def context(db: Session, assignment_id: int, section: str, email: str):
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    if assignment.published_at is None:
        raise HTTPException(404, "Assignment not published")
    if section not in ("group", "individual"):
        raise HTTPException(404, "Evaluation section not found")
    student = db.query(models.Student).filter_by(classroom_id=assignment.classroom_id, email=email).first()
    if student is None:
        raise HTTPException(403, "Classroom membership required")
    pairs = (
        db.query(models.Pair)
        .filter_by(assignment_id=assignment_id, pair_type=section, assigned_to_student_id=student.id, superseded_at=None)
        .order_by(models.Pair.id)
        .all()
    )
    deadline = assignment.group_deadline if section == "group" else assignment.individual_deadline
    if deadline is not None and deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    return assignment, student, pairs, deadline


def require_open(pairs: list[models.Pair], deadline: datetime | None) -> None:
    if not pairs:
        raise HTTPException(403, "No evaluation pairs are assigned")
    if deadline is None or datetime.now(UTC) >= deadline:
        raise HTTPException(409, "Evaluation deadline has passed")


def read_page(db: Session, assignment_id: int, section: str, email: str) -> dict:
    assignment, student, pairs, deadline = context(db, assignment_id, section, email)
    pair_ids = [pair.id for pair in pairs]
    drafts = {
        draft.pair_id: draft.choice
        for draft in db.query(models.DraftChoice).filter(
            models.DraftChoice.student_id == student.id,
            models.DraftChoice.pair_id.in_(pair_ids),
        )
    }
    latest = (
        db.query(models.Submission)
        .filter_by(student_id=student.id, assignment_id=assignment_id, section=section)
        .order_by(models.Submission.id.desc())
        .first()
    )
    submitted = {choice.pair_id: choice.choice for choice in latest.choices} if latest else {}
    criteria = {criterion.id: criterion.name for criterion in assignment.criteria}
    item_ids = {item_id for pair in pairs for item_id in (
        (pair.left_group_id, pair.right_group_id) if section == "group" else (pair.left_id, pair.right_id)
    )}
    model = models.Group if section == "group" else models.Student
    labels = {item.id: item.name if section == "group" else (item.display_name or item.email)
              for item in db.query(model).filter(model.id.in_(item_ids))}
    return {
        "assignment_id": assignment_id,
        "section": section,
        "group_name": student.group.name if student.group else None,
        "deadline": deadline,
        "is_open": bool(pairs) and deadline is not None and datetime.now(UTC) < deadline,
        "submitted_at": as_utc(latest.submitted_at) if latest else None,
        "pairs": [
            {
                "id": pair.id,
                "criterion": criteria[pair.criteria_id],
                "left": labels[pair.left_group_id if section == "group" else pair.left_id],
                "right": labels[pair.right_group_id if section == "group" else pair.right_id],
                "draft_choice": drafts.get(pair.id),
                "submitted_choice": submitted.get(pair.id),
            }
            for pair in pairs
        ],
    }


def save_draft(db: Session, assignment_id: int, section: str, email: str, changes: list[tuple[int, int | None]]) -> dict:
    _, student, pairs, deadline = context(db, assignment_id, section, email)
    require_open(pairs, deadline)
    allowed = {pair.id for pair in pairs}
    if len({pair_id for pair_id, _ in changes}) != len(changes):
        raise HTTPException(422, "Duplicate pair in draft")
    for pair_id, choice in changes:
        if pair_id not in allowed or (choice is not None and choice not in range(1, 6)):
            raise HTTPException(422, "Invalid pair or choice")
    try:
        for pair_id, choice in changes:
            draft = db.query(models.DraftChoice).filter_by(student_id=student.id, pair_id=pair_id).first()
            if choice is None:
                if draft:
                    db.delete(draft)
            elif draft:
                draft.choice = choice
            else:
                db.add(models.DraftChoice(student_id=student.id, pair_id=pair_id, choice=choice))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return read_page(db, assignment_id, section, email)


def submit(db: Session, assignment_id: int, section: str, email: str) -> dict:
    _, student, pairs, deadline = context(db, assignment_id, section, email)
    require_open(pairs, deadline)
    drafts = db.query(models.DraftChoice).filter(
        models.DraftChoice.student_id == student.id,
        models.DraftChoice.pair_id.in_([pair.id for pair in pairs]),
    ).all()
    if not drafts:
        raise HTTPException(422, "Answer at least one pair before submitting")
    snapshot = models.Submission(
        student_id=student.id, assignment_id=assignment_id, section=section, submitted_at=datetime.now(UTC)
    )
    snapshot.choices = [models.SubmissionChoice(pair_id=draft.pair_id, choice=draft.choice) for draft in drafts]
    try:
        db.add(snapshot)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"submission_id": snapshot.id, "submitted_at": snapshot.submitted_at, "answered": len(drafts), "assigned": len(pairs)}
