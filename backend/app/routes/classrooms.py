"""Classrooms endpoints."""

from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .. import crud, models, schemas
from ..auth import Identity, approved_instructors, current_identity
from ..dependencies import get_db, instructor_emails, require_owner, validate_page
from ..reassignment import reassign
from ..roster import import_roster
from ..timezone import as_utc

router = APIRouter(dependencies=[Depends(current_identity)])


@router.get("/me")
def read_me(identity: Identity = Depends(current_identity), db: Session = Depends(get_db)) -> dict:
    memberships = db.query(models.Student).filter_by(email=identity.email).all()
    now = datetime.now(UTC)
    activated = [member for member in memberships if member.activated_at is None]
    if activated:
        for member in activated:
            member.activated_at = now
        db.commit()
    return {"email": identity.email, "is_instructor": identity.is_instructor,
            "classroom_ids": [member.classroom_id for member in memberships]}


@router.post("/classrooms/", response_model=schemas.Classroom)
def create_classroom(
    classroom: schemas.ClassroomCreate,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> models.Classroom:
    if not identity.is_instructor:
        raise HTTPException(status_code=403, detail="Instructor access required")
    return crud.create_classroom(
        db, schemas.ClassroomCreate(name=classroom.name, instructor_emails=identity.email)
    )


@router.get("/classrooms/", response_model=list[schemas.Classroom])
def read_classrooms(
    skip: int = 0,
    limit: int = 100,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> list[models.Classroom]:
    validate_page(skip, limit, 100)
    student_ids = set(db.scalars(select(models.Student.classroom_id).where(models.Student.email == identity.email)))
    visible = [classroom for classroom in db.query(models.Classroom).order_by(models.Classroom.id)
               if classroom.id in student_ids or (identity.is_instructor and identity.email in instructor_emails(classroom))]
    return visible[skip:skip + limit]


@router.post("/classrooms/{classroom_id}/instructors", response_model=schemas.Classroom)
def invite_instructor(
    classroom_id: int, payload: schemas.InstructorInvite,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> models.Classroom:
    classroom = require_owner(classroom_id, identity, db)
    email = str(payload.email).strip().lower()
    if email not in approved_instructors():
        raise HTTPException(422, "Instructor email is not approved")
    emails = instructor_emails(classroom)
    emails.add(email)
    classroom.instructor_emails = ",".join(sorted(emails))
    db.commit()
    db.refresh(classroom)
    return classroom


@router.delete("/classrooms/{classroom_id}/instructors/{email}", response_model=schemas.Classroom)
def remove_instructor(
    classroom_id: int, email: str,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> models.Classroom:
    classroom = require_owner(classroom_id, identity, db)
    emails = instructor_emails(classroom)
    target = email.strip().lower()
    if target not in emails:
        raise HTTPException(404, "Instructor not assigned")
    if len(emails) == 1:
        raise HTTPException(409, "Cannot remove the last instructor")
    emails.remove(target)
    classroom.instructor_emails = ",".join(sorted(emails))
    db.commit()
    db.refresh(classroom)
    return classroom


@router.post("/classrooms/{classroom_id}/roster/import", response_model=schemas.RosterImportResponse)
def import_classroom_roster(
    classroom_id: int,
    payload: schemas.RosterImportRequest,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> schemas.RosterImportResponse:
    require_owner(classroom_id, identity, db)
    result = import_roster(db, classroom_id, payload.csv_text)
    return schemas.RosterImportResponse(imported=len(result.rows), errors=result.errors)


@router.post("/students/", response_model=schemas.Student)
def create_student(
    student: schemas.StudentCreate,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> models.Student:
    require_owner(student.classroom_id, identity, db)
    return crud.create_student(db, student)


@router.get("/students/", response_model=list[schemas.Student])
def read_students(
    classroom_id: int,
    skip: int = 0,
    limit: int = 100,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> list[models.Student]:
    require_owner(classroom_id, identity, db)
    validate_page(skip, limit)
    return db.query(models.Student).filter_by(classroom_id=classroom_id).offset(skip).limit(limit).all()


@router.post("/groups/", response_model=schemas.Group)
def create_group(
    group: schemas.GroupCreate,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> models.Group:
    require_owner(group.classroom_id, identity, db)
    return crud.create_group(db, group)


@router.get("/groups/", response_model=list[schemas.Group])
def read_groups(
    classroom_id: int,
    skip: int = 0,
    limit: int = 100,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> list[models.Group]:
    require_owner(classroom_id, identity, db)
    validate_page(skip, limit)
    return db.query(models.Group).filter_by(classroom_id=classroom_id).offset(skip).limit(limit).all()


@router.put("/classrooms/{classroom_id}/students/{student_id}/group")
def reassign_student_group(
    classroom_id: int, student_id: int, payload: schemas.GroupReassignmentRequest,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> dict:
    require_owner(classroom_id, identity, db)
    try:
        return reassign(db, classroom_id, student_id, payload.group_id, identity.email)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.get("/classrooms/{classroom_id}/reassignments")
def read_reassignments(
    classroom_id: int, identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> list[dict]:
    require_owner(classroom_id, identity, db)
    history = db.query(models.Reassignment).filter_by(classroom_id=classroom_id).order_by(models.Reassignment.id.desc()).all()
    return [{"id": item.id, "student_id": item.student_id, "old_group_id": item.old_group_id,
             "new_group_id": item.new_group_id, "instructor_email": item.instructor_email,
             "changed_at": as_utc(item.changed_at)} for item in history]


@router.get("/classrooms/{classroom_id}/notifications")
def read_notifications(
    classroom_id: int, identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> list[dict]:
    student = db.query(models.Student).filter_by(classroom_id=classroom_id, email=identity.email).first()
    if student is None:
        raise HTTPException(403, "Classroom membership required")
    notifications = db.query(models.Notification).filter_by(student_id=student.id).order_by(models.Notification.id.desc()).limit(20).all()
    return [{"id": item.id, "message": item.message, "created_at": as_utc(item.created_at)} for item in notifications]
