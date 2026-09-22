"""CSV report sheets with spreadsheet formula escaping."""

import csv
from io import StringIO

from sqlalchemy.orm import Session

from . import models
from .reports import assignment_report
from .timezone import as_utc


def _safe(value: object) -> object:
    if hasattr(value, "tzinfo"):
        return as_utc(value).isoformat()
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def sheet_data(db: Session, assignment: models.Assignment, sheet: str) -> tuple[tuple[str, ...], list[dict]]:
    report = assignment_report(db, assignment)
    if sheet == "groups":
        criterion_fields = [(item.id, f"criterion_{item.id}_{item.name}")
                            for item in db.query(models.Criteria).filter_by(assignment_id=assignment.id, is_group=True).order_by(models.Criteria.id)]
        fields = ("group_id", "name", *(field for _, field in criterion_fields), "work_score")
        lookup = {(item["criterion_id"], item["item_id"]): item["weighted_score"] for item in report["criterion_scores"]}
        rows = [{**group, **{field: lookup.get((criterion_id, group["group_id"]))
                             for criterion_id, field in criterion_fields}} for group in report["groups"]]
    elif sheet == "students":
        criterion_fields = [(item.id, f"criterion_{item.id}_{item.name}")
                            for item in db.query(models.Criteria).filter_by(assignment_id=assignment.id, is_group=False).order_by(models.Criteria.id)]
        fields = ("student_id", "email", "group_name", "group_work_score", *(field for _, field in criterion_fields), "individual_work_score",
                  "group_participation_score", "individual_participation_score")
        lookup = {(item["criterion_id"], item["item_id"]): item["weighted_score"] for item in report["criterion_scores"]}
        rows = [{**student, **{field: lookup.get((criterion_id, student["student_id"]))
                               for criterion_id, field in criterion_fields}} for student in report["students"]]
    elif sheet == "pairs":
        fields = ("section", "criterion", "left_id", "right_id", "evaluator", "choice", "submitted_at")
        criteria = {item.id: item.name for item in db.query(models.Criteria).filter_by(assignment_id=assignment.id)}
        pairs = db.query(models.Pair).filter_by(assignment_id=assignment.id, superseded_at=None).order_by(models.Pair.id).all()
        submissions = db.query(models.Submission).filter_by(assignment_id=assignment.id).order_by(models.Submission.id).all()
        latest = {(item.student_id, item.section): item for item in submissions}
        submitted = {choice.pair_id: (choice.choice, item.submitted_at)
                     for item in latest.values() for choice in item.choices}
        submitted.update({vote.pair_id: (vote.choice, vote.submitted_at)
                          for vote in db.query(models.InstructorVote).filter(
                              models.InstructorVote.pair_id.in_([pair.id for pair in pairs]))})
        evaluators = {student_id: f"Evaluator {index}"
                      for index, student_id in enumerate(sorted({pair.assigned_to_student_id for pair in pairs
                                                                    if pair.assigned_to_student_id is not None}), 1)}
        rows = [{
            "section": pair.pair_type, "criterion": criteria[pair.criteria_id],
            "left_id": pair.left_group_id if pair.pair_type == "group" else pair.left_id,
            "right_id": pair.right_group_id if pair.pair_type == "group" else pair.right_id,
            "evaluator": evaluators.get(pair.assigned_to_student_id, "Instructor"),
            "choice": submitted[pair.id][0] if pair.id in submitted else None,
            "submitted_at": submitted[pair.id][1] if pair.id in submitted else None,
        } for pair in pairs]
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
