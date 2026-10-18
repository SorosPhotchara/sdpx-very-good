"""Shared API dependencies and access checks."""

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from . import models
from .auth import Identity
from .database import get_db
from .timezone import as_utc

def require_owner(classroom_id: int, identity: Identity, db: Session) -> models.Classroom:
    classroom = db.get(models.Classroom, classroom_id)
    if classroom is None:
        raise HTTPException(status_code=404, detail="Classroom not found")
    owners = instructor_emails(classroom)
    if not identity.is_instructor or identity.email not in owners:
        raise HTTPException(status_code=403, detail="Instructor access required")
    return classroom


def classroom_has_evaluation(db: Session, classroom_id: int) -> bool:
    """True once any assignment in the classroom is published or owns a pair.

    Instructor-assigned pairs reach the table without setting ``published_at``, so
    both halves matter before anything that would orphan a pair is allowed.
    """
    return db.query(models.Assignment.id).outerjoin(
        models.Pair, models.Pair.assignment_id == models.Assignment.id
    ).filter(
        models.Assignment.classroom_id == classroom_id,
        or_(models.Assignment.published_at.is_not(None), models.Pair.id.is_not(None)),
    ).first() is not None


def instructor_emails(classroom: models.Classroom) -> set[str]:
    return {address.strip().lower() for address in (classroom.instructor_emails or "").split(",") if address.strip()}


def utc_deadline(value):
    return as_utc(value)


def validate_page(skip: int, limit: int, maximum: int = 500) -> None:
    if skip < 0 or not 1 <= limit <= maximum:
        raise HTTPException(422, "Invalid pagination")
