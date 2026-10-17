"""Platform administrator actions."""

from fastapi import APIRouter, Depends, HTTPException
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
        "instructor_count": len(approved_instructors()),
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
    identity: Identity = Depends(current_identity),
) -> list[dict]:
    require_admin(identity)
    return [{"email": email, "source": "environment"} for email in sorted(approved_instructors())]


@router.post("/instructors")
def approve_instructor(
    payload: schemas.InstructorApprovalCreate,
    identity: Identity = Depends(current_identity),
) -> None:
    require_admin(identity)
    raise HTTPException(status_code=409, detail="Configure INSTRUCTOR_EMAILS to change the instructor allowlist")


@router.delete("/instructors/{email}", status_code=204)
def revoke_instructor(
    email: str,
    identity: Identity = Depends(current_identity),
) -> None:
    require_admin(identity)
    raise HTTPException(status_code=409, detail="Configure INSTRUCTOR_EMAILS to change the instructor allowlist")
