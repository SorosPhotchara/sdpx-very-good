"""Compute current work and participation scores from submitted snapshots."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from . import models
from .scoring import PairVote, score_items


def assignment_report(db: Session, assignment: models.Assignment) -> dict:
    students = db.query(models.Student).filter_by(classroom_id=assignment.classroom_id).order_by(models.Student.id).all()
    groups = db.query(models.Group).filter_by(classroom_id=assignment.classroom_id).order_by(models.Group.id).all()
    criteria = db.query(models.Criteria).filter_by(assignment_id=assignment.id).all()
    pairs = db.query(models.Pair).filter_by(assignment_id=assignment.id, superseded_at=None).all()
    submissions = db.query(models.Submission).filter_by(assignment_id=assignment.id).order_by(models.Submission.id).all()
    latest = {(item.student_id, item.section): item for item in submissions}
    submitted = {choice.pair_id: choice.choice for item in latest.values() for choice in item.choices}
    instructor_votes = {vote.pair_id: vote.choice for vote in db.query(models.InstructorVote).filter(
        models.InstructorVote.pair_id.in_([pair.id for pair in pairs]))}
    submitted.update(instructor_votes)
    students_by_id = {student.id: student for student in students}
    group_scores: dict[int, float | None] = {group.id: None for group in groups}
    individual_scores: dict[int, float | None] = {student.id: None for student in students}
    coverage = []
    criterion_scores = []

    for criterion in criteria:
        criterion_pairs = [pair for pair in pairs if pair.criteria_id == criterion.id]
        section = "group" if criterion.is_group else "individual"
        deadline = assignment.group_deadline if criterion.is_group else assignment.individual_deadline
        if deadline is not None and deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)
        final = deadline is not None and datetime.now(UTC) >= deadline
        item_ids = [item.id for item in (groups if criterion.is_group else students)]
        votes = [PairVote(
            left_id=pair.left_group_id if criterion.is_group else pair.left_id,
            right_id=pair.right_group_id if criterion.is_group else pair.right_id,
            choice=submitted[pair.id],
            weight=assignment.instructor_weight if pair.assigned_to_instructor_email else 1.0,
        ) for pair in criterion_pairs if pair.id in submitted]
        scores = score_items(
            item_ids, votes,
            assignment.group_score if criterion.is_group else assignment.individual_score,
            criterion.weight / 100, final,
        )
        target = group_scores if criterion.is_group else individual_scores
        for item_id, result in scores.items():
            criterion_scores.append({
                "criterion_id": criterion.id, "criterion": criterion.name, "section": section,
                "item_id": item_id, "average_points": result.average_points,
                "relative_score": result.relative_score, "weighted_score": result.weighted_score,
                "effective_votes": result.effective_votes,
            })
            if result.weighted_score is not None:
                target[item_id] = (target[item_id] or 0) + result.weighted_score
        pair_counts: dict[tuple[int, int], int] = {}
        for pair in criterion_pairs:
            left = pair.left_group_id if criterion.is_group else pair.left_id
            right = pair.right_group_id if criterion.is_group else pair.right_id
            key = tuple(sorted((left, right)))
            pair_counts[key] = pair_counts.get(key, 0) + int(pair.id in submitted)
        for (left, right), count in sorted(pair_counts.items()):
            coverage.append({"section": section, "criterion": criterion.name, "left_id": left,
                             "right_id": right, "votes": count, "missing_to_five": max(0, 5 - count)})

    assigned: dict[tuple[int, str], int] = {}
    answered: dict[tuple[int, str], int] = {}
    for pair in pairs:
        if pair.assigned_to_student_id is None:
            continue
        key = (pair.assigned_to_student_id, pair.pair_type)
        assigned[key] = assigned.get(key, 0) + 1
        answered[key] = answered.get(key, 0) + int(pair.id in submitted)

    rows = []
    for student in students:
        group = next((item for item in groups if item.id == student.group_id), None)
        member_count = sum(member.group_id == student.group_id for member in students)
        participation = {}
        for section, maximum in (("group", assignment.group_participation_max),
                                 ("individual", assignment.individual_participation_max)):
            eligible = section == "group" or member_count >= 3
            total = assigned.get((student.id, section), 0)
            done = answered.get((student.id, section), 0)
            participation[section] = None if not eligible else maximum * done / total if total else 0.0
        rows.append({
            "student_id": student.id, "email": student.email,
            "group_id": student.group_id, "group_name": group.name if group else None,
            "group_work_score": group_scores.get(student.group_id),
            "individual_work_score": individual_scores[student.id] if member_count >= 3 else None,
            "group_participation_score": participation["group"],
            "individual_participation_score": participation["individual"],
        })
    return {"assignment_id": assignment.id, "title": assignment.title, "students": rows,
            "groups": [{"group_id": group.id, "name": group.name, "work_score": group_scores[group.id]} for group in groups],
            "coverage": coverage, "criterion_scores": criterion_scores,
            "group_final": _is_final(assignment.group_deadline),
            "individual_final": _is_final(assignment.individual_deadline)}


def _is_final(deadline: datetime | None) -> bool:
    if deadline is None:
        return False
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    return datetime.now(UTC) >= deadline
