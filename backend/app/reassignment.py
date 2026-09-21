"""Move a student between groups while preserving valid pair assignments."""

from collections import defaultdict
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import models
from .instructor_evaluation import deadline_for
from .publish import build_plan


def _pair_key(pair: models.Pair) -> tuple:
    return (
        pair.criteria_id, pair.pair_type,
        pair.left_group_id if pair.pair_type == "group" else pair.left_id,
        pair.right_group_id if pair.pair_type == "group" else pair.right_id,
        pair.assigned_to_student_id,
    )


def _planned_key(item) -> tuple:
    allocation = item.allocation
    return (item.criterion_id, allocation.kind, allocation.left_id,
            allocation.right_id, allocation.evaluator_id)


def reassign(db: Session, classroom_id: int, student_id: int, target_group_id: int,
             instructor_email: str) -> dict:
    student = db.get(models.Student, student_id)
    target = db.get(models.Group, target_group_id)
    if student is None or student.classroom_id != classroom_id:
        raise HTTPException(404, "Student not found in classroom")
    if target is None or target.classroom_id != classroom_id:
        raise HTTPException(422, "Target group is outside the classroom")
    if student.group_id is None:
        raise HTTPException(422, "Student has no current group")
    if student.group_id == target.id:
        raise HTTPException(422, "Student is already in this group")
    assignments = db.query(models.Assignment).filter_by(classroom_id=classroom_id).all()
    now = datetime.now(UTC)
    for assignment in assignments:
        for criterion in assignment.criteria:
            deadline = deadline_for(assignment, criterion.is_group)
            if deadline is None or deadline <= now:
                raise HTTPException(409, "Group changes are closed after an evaluation deadline")

    old_group_id = student.group_id
    affected = {student.id}
    changed_pairs = 0
    try:
        student.group_id = target.id
        student.group_name = target.name
        db.flush()
        for assignment in assignments:
            active_pairs = db.query(models.Pair).filter_by(assignment_id=assignment.id, superseded_at=None).all()
            if not active_pairs:
                continue
            available: dict[tuple, list[models.Pair]] = defaultdict(list)
            for pair in active_pairs:
                if pair.assigned_to_student_id is not None:
                    available[_pair_key(pair)].append(pair)
            for planned in build_plan(db, assignment.id):
                key = _planned_key(planned)
                if available[key]:
                    available[key].pop()
                    continue
                allocation = planned.allocation
                db.add(models.Pair(
                    assignment_id=assignment.id, criteria_id=planned.criterion_id,
                    pair_type=allocation.kind, assigned_to_student_id=allocation.evaluator_id,
                    left_group_id=allocation.left_id if allocation.kind == "group" else None,
                    right_group_id=allocation.right_id if allocation.kind == "group" else None,
                    left_id=allocation.left_id if allocation.kind == "individual" else None,
                    right_id=allocation.right_id if allocation.kind == "individual" else None,
                ))
                affected.add(allocation.evaluator_id)
                changed_pairs += 1
            for remaining in available.values():
                for pair in remaining:
                    pair.superseded_at = now
                    affected.add(pair.assigned_to_student_id)
                    changed_pairs += 1
            for pair in active_pairs:
                if pair.assigned_to_instructor_email is None or pair.pair_type != "individual":
                    continue
                left = db.get(models.Student, pair.left_id)
                right = db.get(models.Student, pair.right_id)
                member_count = db.query(models.Student).filter_by(group_id=left.group_id).count()
                if left.group_id != right.group_id or left.group_id is None or member_count < 3:
                    pair.superseded_at = now
                    changed_pairs += 1
        db.add(models.Reassignment(
            classroom_id=classroom_id, student_id=student.id, old_group_id=old_group_id,
            new_group_id=target.id, instructor_email=instructor_email, changed_at=now,
        ))
        db.add_all(models.Notification(
            student_id=affected_id, message="Group membership or pair assignments changed. Review your evaluations.",
            created_at=now,
        ) for affected_id in affected)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"student_id": student.id, "old_group_id": old_group_id,
            "new_group_id": target.id, "changed_pairs": changed_pairs, "notified_students": len(affected)}
