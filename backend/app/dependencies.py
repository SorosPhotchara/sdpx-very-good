"""Shared API dependencies and access checks."""

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from . import models
from .auth import Identity
from .database import get_db
from .timezone import as_utc

OWNER = "OWNER"
CO_TEACHER = "CO_TEACHER"
TA = "TA"
# §3: who may do what. Teachers set up and evaluate; staff also includes the TA,
# who looks after the roster but neither evaluates nor sees results.
TEACHERS = frozenset({OWNER, CO_TEACHER})
STAFF = frozenset({OWNER, CO_TEACHER, TA})


def staff_role(db: Session, classroom_id: int, email: str) -> str | None:
    return db.query(models.ClassroomStaff.role).filter(
        models.ClassroomStaff.classroom_id == classroom_id,
        func.lower(func.trim(models.ClassroomStaff.email)) == (email or "").strip().lower(),
    ).scalar()


def require_role(classroom_id: int, identity: Identity, db: Session,
                 allowed: frozenset[str]) -> models.Classroom:
    """Check the caller's role in this classroom, server side every time.

    FR-AUTHZ-01: the UI hiding a control is never the check. A caller with no
    role here gets 404 rather than 403, so the response cannot be used to find
    out which classrooms exist (FR-AUTHZ-02).
    """
    classroom = db.get(models.Classroom, classroom_id)
    if classroom is None:
        raise HTTPException(status_code=404, detail="Classroom not found")
    role = staff_role(db, classroom_id, identity.email)
    if role is None or not identity.is_instructor:
        raise HTTPException(status_code=404, detail="Classroom not found")
    if role not in allowed:
        raise HTTPException(status_code=403,
                            detail=f"This action needs one of: {', '.join(sorted(allowed))}")
    return classroom


def require_owner(classroom_id: int, identity: Identity, db: Session) -> models.Classroom:
    return require_role(classroom_id, identity, db, frozenset({OWNER}))


def require_teacher(classroom_id: int, identity: Identity, db: Session) -> models.Classroom:
    return require_role(classroom_id, identity, db, TEACHERS)


def require_staff(classroom_id: int, identity: Identity, db: Session) -> models.Classroom:
    return require_role(classroom_id, identity, db, STAFF)


def allowed_domains(classroom: models.Classroom) -> set[str]:
    return {part.strip().lower().lstrip("@")
            for part in (classroom.allowed_email_domains or "").split(",") if part.strip()}


def domain_allowed(classroom: models.Classroom, email: str) -> bool:
    """FR-AUTH-02: an empty list accepts any domain."""
    domains = allowed_domains(classroom)
    if not domains:
        return True
    _, _, domain = (email or "").strip().lower().rpartition("@")
    return domain in domains


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


def instructor_emails(db: Session, classroom: models.Classroom) -> set[str]:
    """Everyone who may evaluate as an instructor here, i.e. the teachers."""
    return {email.strip().lower() for (email,) in db.query(models.ClassroomStaff.email).filter(
        models.ClassroomStaff.classroom_id == classroom.id,
        models.ClassroomStaff.role.in_(TEACHERS))}


def utc_deadline(value):
    return as_utc(value)


def validate_page(skip: int, limit: int, maximum: int = 500) -> None:
    if skip < 0 or not 1 <= limit <= maximum:
        raise HTTPException(422, "Invalid pagination")
