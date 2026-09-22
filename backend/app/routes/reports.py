"""Reports endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from .. import models
from ..auth import Identity, current_identity
from ..dependencies import get_db, require_owner
from ..export import export_csv
from ..reports import assignment_report
from ..xlsx_export import export_xlsx

router = APIRouter(dependencies=[Depends(current_identity)])


@router.get("/assignments/{assignment_id}/report")
def read_assignment_report(
    assignment_id: int, identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> dict:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    require_owner(assignment.classroom_id, identity, db)
    return assignment_report(db, assignment)


@router.get("/assignments/{assignment_id}/my-scores")
def read_my_scores(
    assignment_id: int, identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> dict:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    if assignment.published_at is None:
        raise HTTPException(404, "Assignment not published")
    if not db.query(models.Student.id).filter_by(classroom_id=assignment.classroom_id, email=identity.email).first():
        raise HTTPException(403, "Classroom membership required")
    report = assignment_report(db, assignment)
    row = next((row for row in report["students"] if row["email"] == identity.email), None)
    return row


@router.get("/assignments/{assignment_id}/report/{sheet}.csv")
def download_report_csv(
    assignment_id: int, sheet: str,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> Response:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    require_owner(assignment.classroom_id, identity, db)
    try:
        content = export_csv(db, assignment, sheet)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error
    return Response(content, media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="assignment-{assignment_id}-{sheet}.csv"'
    })


@router.get("/assignments/{assignment_id}/report.xlsx")
def download_report_xlsx(
    assignment_id: int, identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> Response:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    require_owner(assignment.classroom_id, identity, db)
    return Response(export_xlsx(db, assignment), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="assignment-{assignment_id}.xlsx"'})
