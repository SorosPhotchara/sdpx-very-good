"""Shared API dependencies and access checks."""

from fastapi import HTTPException
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


def instructor_emails(classroom: models.Classroom) -> set[str]:
    return {address.strip().lower() for address in (classroom.instructor_emails or "").split(",") if address.strip()}


def utc_deadline(value):
    return as_utc(value)


def validate_page(skip: int, limit: int, maximum: int = 500) -> None:
    if skip < 0 or not 1 <= limit <= maximum:
        raise HTTPException(422, "Invalid pagination")
