"""Reports endpoints."""

import re
from datetime import UTC, datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from .. import models
from ..auth import Identity, current_identity
from ..dependencies import get_db, require_owner
from ..export import export_csv
from ..reports import assignment_report, raw_pair_responses
from ..xlsx_export import export_xlsx

router = APIRouter(dependencies=[Depends(current_identity)])


def _export_disposition(assignment: models.Assignment, report_type: str, extension: str) -> str:
    def part(value: str, fallback: str) -> str:
        cleaned = re.sub(r'[\x00-\x1f\x7f<>:"/\\|?*]+', "_", value.strip())
        cleaned = re.sub(r"_+", "_", re.sub(r"\s+", "_", cleaned)).strip("._")
        return cleaned[:80].rstrip("._") or fallback

    date = datetime.now(UTC).strftime("%Y%m%d")
    filename = (f"{part(assignment.classroom.name, f'classroom-{assignment.classroom_id}')}_"
                f"{part(assignment.title, f'assignment-{assignment.id}')}_{report_type}_{date}.{extension}")
    fallback = filename if filename.isascii() else f"classroom-{assignment.classroom_id}_assignment-{assignment.id}_{report_type}_{date}.{extension}"
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quote(filename, safe="")}'


@router.get("/assignments/{assignment_id}/report")
def read_assignment_report(
    assignment_id: int, identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> dict:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    require_owner(assignment.classroom_id, identity, db)
    return assignment_report(db, assignment)


@router.get("/assignments/{assignment_id}/report/raw-pairs")
def read_raw_pair_responses(
    assignment_id: int, identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> list[dict]:
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    require_owner(assignment.classroom_id, identity, db)
    return raw_pair_responses(db, assignment)


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
    if row is None:
        raise HTTPException(404, "Scores not found")
    # The student view needs the same interim/final state the instructor report carries,
    # so the page can label rolling scores before each section's deadline.
    return {**row, "group_final": report["group_final"], "individual_final": report["individual_final"]}


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
        "Content-Disposition": _export_disposition(assignment, {
            "groups": "group_summary", "students": "individual_summary", "pairs": "raw_pairs",
        }[sheet], "csv")
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
                    headers={"Content-Disposition": _export_disposition(assignment, "report", "xlsx")})
