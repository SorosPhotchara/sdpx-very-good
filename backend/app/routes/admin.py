"""Platform administrator actions."""

import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import Identity, approved_instructors, current_identity
from ..dependencies import get_db

router = APIRouter(prefix="/admin", dependencies=[Depends(current_identity)])


def require_admin(identity: Identity) -> None:
    if not identity.is_admin:
        raise HTTPException(status_code=403, detail="Administrator access required")


@router.get("/overview")
def admin_overview(
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> dict:
    require_admin(identity)
    classrooms = db.query(models.Classroom).order_by(models.Classroom.name).all()
    return {
        "classroom_count": len(classrooms),
        "student_count": db.query(models.Student.email).distinct().count(),
        "instructor_count": len(approved_instructors(db)),
        "classrooms": [{
            "id": classroom.id,
            "name": classroom.name,
            "instructors": sorted(email.strip() for email in classroom.instructor_emails.split(",") if email.strip()),
            "student_count": db.query(models.Student.id).filter_by(classroom_id=classroom.id).count(),
            "assignment_count": db.query(models.Assignment.id).filter_by(classroom_id=classroom.id).count(),
        } for classroom in classrooms],
    }


@router.get("/instructors", response_model=list[schemas.InstructorApprovalRead])
def list_instructors(
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> list[dict]:
    require_admin(identity)
    env_emails = {
        email.strip().lower()
        for email in os.environ.get("INSTRUCTOR_EMAILS", "").split(",")
        if email.strip()
    }
    records = {
        item.email: {
            "email": item.email,
            "source": "database",
            "approved_by": item.approved_by,
            "approved_at": item.approved_at,
        }
        for item in db.query(models.InstructorApproval).order_by(models.InstructorApproval.email)
    }
    for email in env_emails:
        records.setdefault(email, {"email": email})
        records[email]["source"] = "environment"
    return sorted(records.values(), key=lambda item: item["email"])


@router.post("/instructors", response_model=schemas.InstructorApprovalRead, status_code=201)
def approve_instructor(
    payload: schemas.InstructorApprovalCreate,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> dict:
    require_admin(identity)
    email = str(payload.email).strip().lower()
    if email in approved_instructors(db):
        raise HTTPException(status_code=409, detail="Instructor is already approved")
    record = models.InstructorApproval(email=email, approved_by=identity.email, approved_at=datetime.now(UTC))
    db.add(record)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Instructor is already approved") from error
    db.refresh(record)
    return {
        "email": record.email,
        "source": "database",
        "approved_by": record.approved_by,
        "approved_at": record.approved_at,
    }


@router.delete("/instructors/{email}", status_code=204)
def revoke_instructor(
    email: str,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> None:
    require_admin(identity)
    target = email.strip().lower()
    env_emails = {
        address.strip().lower()
        for address in os.environ.get("INSTRUCTOR_EMAILS", "").split(",")
        if address.strip()
    }
    if target in env_emails:
        raise HTTPException(status_code=409, detail="Environment-approved instructors must be changed in configuration")
    record = db.get(models.InstructorApproval, target)
    if record is None:
        raise HTTPException(status_code=404, detail="Instructor approval not found")
    db.delete(record)
    db.commit()
