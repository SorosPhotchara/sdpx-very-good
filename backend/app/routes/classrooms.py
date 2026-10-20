"""Classrooms endpoints."""

from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .. import crud, models, schemas
from ..auth import Identity, approved_instructors, current_identity
from ..dependencies import (OWNER, STAFF, TEACHERS, allowed_domains, classroom_has_evaluation,
                            domain_allowed,
                            get_db, require_owner, require_role, require_staff, staff_role,
                            validate_page)
from ..reassignment import preview_reassignment, reassign
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
    return {"email": identity.email, "is_instructor": identity.is_instructor, "is_admin": identity.is_admin,
            "picture_url": identity.picture_url,
            "classroom_ids": [member.classroom_id for member in memberships]}


@router.post("/classrooms/", response_model=schemas.Classroom)
def create_classroom(
    classroom: schemas.ClassroomCreate,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> models.Classroom:
    if not identity.is_instructor:
        raise HTTPException(status_code=403, detail="Instructor access required")
    return crud.create_classroom(db, classroom, identity.email)


@router.get("/classrooms/", response_model=list[schemas.Classroom])
def read_classrooms(
    skip: int = 0,
    limit: int = 100,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> list[models.Classroom]:
    validate_page(skip, limit, 100)
    student_ids = set(db.scalars(select(models.Student.classroom_id).where(models.Student.email == identity.email)))
    staffed = set(db.scalars(select(models.ClassroomStaff.classroom_id).where(
        func.lower(func.trim(models.ClassroomStaff.email)) == identity.email.strip().lower())))
    visible = [classroom for classroom in db.query(models.Classroom).order_by(models.Classroom.id)
               if classroom.id in student_ids or (identity.is_instructor and classroom.id in staffed)]
    return visible[skip:skip + limit]


@router.patch("/classrooms/{classroom_id}", response_model=schemas.Classroom)
def rename_classroom(
    classroom_id: int, payload: schemas.ClassroomRename,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> models.Classroom:
    classroom = require_owner(classroom_id, identity, db)
    db.refresh(classroom, with_for_update=True)
    require_owner(classroom_id, identity, db)
    classroom.name = payload.name
    db.commit()
    db.refresh(classroom)
    return classroom


@router.delete("/classrooms/{classroom_id}", status_code=204)
def delete_classroom(
    classroom_id: int, payload: schemas.ClassroomRename,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> Response:
    classroom = require_owner(classroom_id, identity, db)
    db.refresh(classroom, with_for_update=True)
    require_owner(classroom_id, identity, db)
    if payload.name != classroom.name:
        raise HTTPException(409, "Classroom name changed or confirmation does not match. Refresh and try again.")
    crud.delete_classroom(db, classroom_id, deleted_by=identity.email)
    return Response(status_code=204)


@router.post("/classrooms/{classroom_id}/instructors", response_model=schemas.Classroom)
def invite_instructor(
    classroom_id: int, payload: schemas.InstructorInvite,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> models.Classroom:
    classroom = require_owner(classroom_id, identity, db)
    email = str(payload.email).strip().lower()
    role = (getattr(payload, "role", None) or "CO_TEACHER").strip().upper()
    if role not in STAFF:
        raise HTTPException(422, f"Role must be one of: {', '.join(sorted(STAFF))}")
    # A TA never evaluates or sees results, so they do not need to be in the
    # instructor allowlist; a teacher does (§3, FR-AUTH-02's sibling control).
    if role in TEACHERS and email not in approved_instructors():
        raise HTTPException(422, "Instructor email must be in INSTRUCTOR_EMAILS")
    if not domain_allowed(classroom, email):
        raise HTTPException(422, "Email domain is not allowed for this classroom")
    existing = db.query(models.ClassroomStaff).filter(
        models.ClassroomStaff.classroom_id == classroom_id,
        func.lower(func.trim(models.ClassroomStaff.email)) == email).one_or_none()
    if existing is None:
        db.add(models.ClassroomStaff(classroom_id=classroom_id, email=email, role=role,
                                     added_at=datetime.now(UTC)))
    else:
        existing.role = role
    db.commit()
    db.refresh(classroom)
    return classroom


@router.delete("/classrooms/{classroom_id}/instructors/{email}", response_model=schemas.Classroom)
def remove_instructor(
    classroom_id: int, email: str,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> models.Classroom:
    classroom = require_owner(classroom_id, identity, db)
    target = email.strip().lower()
    member = db.query(models.ClassroomStaff).filter(
        models.ClassroomStaff.classroom_id == classroom_id,
        func.lower(func.trim(models.ClassroomStaff.email)) == target).one_or_none()
    if member is None:
        raise HTTPException(404, "Instructor not assigned")
    owners = db.query(models.ClassroomStaff.id).filter_by(
        classroom_id=classroom_id, role=OWNER).count()
    if member.role == OWNER and owners == 1:
        raise HTTPException(409, "Cannot remove the last instructor")
    db.delete(member)
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
    classroom = require_staff(classroom_id, identity, db)
    if db.query(models.Assignment.id).filter_by(classroom_id=classroom_id).filter(
        models.Assignment.published_at.is_not(None)
    ).first():
        raise HTTPException(409, "Cannot import students after an assignment is published")
    result = import_roster(db, classroom_id, payload.csv_text, allowed_domains(classroom))
    return schemas.RosterImportResponse(imported=len(result.rows), errors=result.errors)


@router.post("/students/", response_model=schemas.Student)
def create_student(
    student: schemas.StudentCreate,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> models.Student:
    require_staff(student.classroom_id, identity, db)
    if db.query(models.Assignment.id).filter_by(classroom_id=student.classroom_id).filter(
        models.Assignment.published_at.is_not(None)
    ).first():
        raise HTTPException(409, "Cannot add students after an assignment is published")
    try:
        return crud.create_student(db, student)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "Student email is already in this classroom") from error


@router.get("/students/", response_model=list[schemas.Student])
def read_students(
    classroom_id: int,
    skip: int = 0,
    limit: int = 100,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> list[models.Student]:
    require_staff(classroom_id, identity, db)
    validate_page(skip, limit)
    return db.query(models.Student).filter_by(classroom_id=classroom_id).offset(skip).limit(limit).all()


@router.delete("/classrooms/{classroom_id}/students/{student_id}", status_code=204)
def remove_student(
    classroom_id: int, student_id: int, payload: schemas.StudentRemoval,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> Response:
    classroom = require_staff(classroom_id, identity, db)
    student = db.get(models.Student, student_id)
    if student is None or student.classroom_id != classroom_id:
        raise HTTPException(404, "Student not found in classroom")
    db.refresh(classroom, with_for_update=True)
    require_staff(classroom_id, identity, db)
    if classroom_has_evaluation(db, classroom_id):
        raise HTTPException(409, "Cannot remove a student after an evaluation exists")
    if payload.email != (student.email or "").strip().lower():
        raise HTTPException(409, "Student roster changed or confirmation does not match. Refresh and try again.")
    crud.delete_student(db, student_id)
    return Response(status_code=204)


@router.post("/groups/", response_model=schemas.Group)
def create_group(
    group: schemas.GroupCreate,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> models.Group:
    require_staff(group.classroom_id, identity, db)
    return crud.create_group(db, group)


@router.get("/groups/", response_model=list[schemas.Group])
def read_groups(
    classroom_id: int,
    skip: int = 0,
    limit: int = 100,
    identity: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
) -> list[models.Group]:
    require_staff(classroom_id, identity, db)
    validate_page(skip, limit)
    return db.query(models.Group).filter_by(classroom_id=classroom_id).offset(skip).limit(limit).all()


@router.get("/classrooms/{classroom_id}/students/{student_id}/group/preview")
def preview_student_group_reassignment(
    classroom_id: int, student_id: int, group_id: int,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> dict:
    require_staff(classroom_id, identity, db)
    try:
        return preview_reassignment(db, classroom_id, student_id, group_id)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.put("/classrooms/{classroom_id}/students/{student_id}/group")
def reassign_student_group(
    classroom_id: int, student_id: int, payload: schemas.GroupReassignmentRequest,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> dict:
    require_staff(classroom_id, identity, db)
    try:
        return reassign(db, classroom_id, student_id, payload.group_id, identity.email)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.get("/classrooms/{classroom_id}/reassignments")
def read_reassignments(
    classroom_id: int, identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> list[dict]:
    require_staff(classroom_id, identity, db)
    history = db.query(models.Reassignment).filter_by(classroom_id=classroom_id).order_by(models.Reassignment.id.desc()).all()
    # Names make the audit trail readable; a removed group keeps its id with no name.
    students = {item.id: item.email for item in db.query(models.Student).filter_by(classroom_id=classroom_id)}
    groups = {item.id: item.name for item in db.query(models.Group).filter_by(classroom_id=classroom_id)}
    return [{"id": item.id, "student_id": item.student_id, "student_email": students.get(item.student_id),
             "old_group_id": item.old_group_id, "old_group_name": groups.get(item.old_group_id),
             "new_group_id": item.new_group_id, "new_group_name": groups.get(item.new_group_id),
             "instructor_email": item.instructor_email,
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
