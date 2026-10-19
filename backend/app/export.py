"""CSV report sheets with spreadsheet formula escaping."""

import csv
from io import StringIO

from sqlalchemy.orm import Session

from . import models
from .reports import assignment_report, raw_pair_responses
from .timezone import as_utc


def _safe(value: object) -> object:
    if hasattr(value, "tzinfo"):
        return as_utc(value).isoformat()
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _student_total(student: dict) -> float | None:
    """Work plus participation across both sections; None when the student has no score at all.

    Exempt components are None rather than zero, so they are skipped instead of
    dragging the total down.
    """
    parts = [student["group_work_score"], student["individual_work_score"],
             student["group_participation_score"], student["individual_participation_score"]]
    scored = [value for value in parts if value is not None]
    return sum(scored) if scored else None


def sheet_data(db: Session, assignment: models.Assignment, sheet: str) -> tuple[tuple[str, ...], list[dict]]:
    if sheet == "groups":
        report = assignment_report(db, assignment)
        criterion_fields = [(item.id, f"criterion_{item.id}_{item.name}")
                            for item in db.query(models.Criteria).filter_by(assignment_id=assignment.id, is_group=True).order_by(models.Criteria.id)]
        fields = ("group_id", "name", *(field for _, field in criterion_fields), "work_score")
        lookup = {(item["criterion_id"], item["item_id"]): item["weighted_score"] for item in report["criterion_scores"]}
        rows = [{**group, **{field: lookup.get((criterion_id, group["group_id"]))
                             for criterion_id, field in criterion_fields}} for group in report["groups"]]
    elif sheet == "students":
        report = assignment_report(db, assignment)
        criterion_fields = [(item.id, f"criterion_{item.id}_{item.name}")
                            for item in db.query(models.Criteria).filter_by(assignment_id=assignment.id, is_group=False).order_by(models.Criteria.id)]
        fields = ("student_id", "email", "group_name", "group_work_score", *(field for _, field in criterion_fields), "individual_work_score",
                  "group_participation_score", "individual_participation_score", "total_score")
        lookup = {(item["criterion_id"], item["item_id"]): item["weighted_score"] for item in report["criterion_scores"]}
        rows = [{**student, **{field: lookup.get((criterion_id, student["student_id"]))
                               for criterion_id, field in criterion_fields},
                 "total_score": _student_total(student)} for student in report["students"]]
    elif sheet == "pairs":
        fields = ("section", "criterion", "left_id", "right_id", "evaluator", "choice", "submitted_at")
        raw = raw_pair_responses(db, assignment)
        evaluators = {student_id: f"Evaluator {index}" for index, student_id in enumerate(
            sorted({row["evaluator_student_id"] for row in raw if row["evaluator_student_id"] is not None}), 1)}
        rows = [{
            "section": row["section"], "criterion": row["criterion"],
            "left_id": row["left_id"], "right_id": row["right_id"],
            "evaluator": evaluators.get(row["evaluator_student_id"], "Instructor"),
            "choice": row["choice"], "submitted_at": row["submitted_at"],
        } for row in raw]
    else:
        raise ValueError("Unknown report sheet")
    return fields, rows


def export_csv(db: Session, assignment: models.Assignment, sheet: str) -> str:
    fields, rows = sheet_data(db, assignment, sheet)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(fields)
    for row in rows:
        writer.writerow([_safe(row[field]) if row[field] is not None else "" for field in fields])
    return output.getvalue()
