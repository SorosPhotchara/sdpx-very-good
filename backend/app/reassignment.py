"""Preview and apply group moves while retaining eligible pair assignments."""

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models
from .instructor_evaluation import deadline_for
from .publish import PlannedPair, build_plan


@dataclass
class MoveEffects:
    new_pairs: list[PlannedPair]
    superseded_pairs: list[models.Pair]
    notified_students: set[int]
    affected_submissions: int

    def summary(self) -> dict[str, int]:
        added = len(self.new_pairs)
        removed = len(self.superseded_pairs)
        return {
            "changed_pairs": added + removed,
            "new_pairs": added,
            "superseded_pairs": removed,
            "affected_submissions": self.affected_submissions,
            "notified_students": len(self.notified_students),
        }


def _validate_move(db: Session, classroom_id: int, student_id: int,
                   target_group_id: int) -> tuple[models.Student, models.Group, list[models.Assignment]]:
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
        if assignment.published_at is None:
            continue
        for criterion in assignment.criteria:
            deadline = deadline_for(assignment, criterion.is_group)
            if deadline is None or deadline <= now:
                raise HTTPException(409, "Group changes are closed after an evaluation deadline")
    return student, target, assignments


def _items(pair: models.Pair) -> tuple[int | None, int | None]:
    if pair.pair_type == "group":
        return pair.left_group_id, pair.right_group_id
    return pair.left_id, pair.right_id


def _eligible_after_move(pair: models.Pair, memberships: dict[int, int | None],
                         group_sizes: Counter[int]) -> bool:
    left, right = _items(pair)
    if left is None or right is None or left == right:
        return False
    if pair.pair_type == "group":
        if not group_sizes[left] or not group_sizes[right]:
            return False
        evaluator_group = memberships.get(pair.assigned_to_student_id)
        return pair.assigned_to_student_id is None or evaluator_group not in (left, right)
    if pair.pair_type == "individual":
        group_id = memberships.get(left)
        if group_id is None or group_id != memberships.get(right) or group_sizes[group_id] < 3:
            return False
        evaluator_id = pair.assigned_to_student_id
        return evaluator_id is None or (
            evaluator_id not in (left, right) and memberships.get(evaluator_id) == group_id
        )
    return False


def _effects_after_move(db: Session, assignments: list[models.Assignment],
                        moved_student_id: int) -> MoveEffects:
    classroom_id = assignments[0].classroom_id if assignments else db.get(models.Student, moved_student_id).classroom_id
    students = db.query(models.Student).filter_by(classroom_id=classroom_id).all()
    memberships = {student.id: student.group_id for student in students}
    group_sizes = Counter(group_id for group_id in memberships.values() if group_id is not None)
    added: list[PlannedPair] = []
    removed: list[models.Pair] = []
    affected = {moved_student_id}

    for assignment in assignments:
        if assignment.published_at is None:
            continue
        active = db.query(models.Pair).filter_by(assignment_id=assignment.id, superseded_at=None).all()
        valid_student_evaluators: dict[tuple[int, int, int], set[int]] = {}
        for pair in active:
            if not _eligible_after_move(pair, memberships, group_sizes):
                removed.append(pair)
                if pair.assigned_to_student_id is not None:
                    affected.add(pair.assigned_to_student_id)
                continue
            if pair.assigned_to_student_id is not None:
                left, right = _items(pair)
                key = (pair.criteria_id, *sorted((left, right)))
                valid_student_evaluators.setdefault(key, set()).add(pair.assigned_to_student_id)

        plan = build_plan(db, assignment.id)
        planned_targets = Counter(
            (planned.criterion_id, *sorted((planned.allocation.left_id, planned.allocation.right_id)))
            for planned in plan
        )
        for planned in plan:
            allocation = planned.allocation
            key = (planned.criterion_id, *sorted((allocation.left_id, allocation.right_id)))
            evaluators = valid_student_evaluators.setdefault(key, set())
            if len(evaluators) >= planned_targets[key] or allocation.evaluator_id in evaluators:
                continue
            added.append(planned)
            evaluators.add(allocation.evaluator_id)
            affected.add(allocation.evaluator_id)

        # Filling every pair up to its target can still leave a student whose own pairs
        # were all superseded with an empty section, so hand those evaluators a pair the
        # post-move plan already considers legal for them.
        planned_by_evaluator: dict[tuple[int, int], list[PlannedPair]] = {}
        for planned in plan:
            planned_by_evaluator.setdefault(
                (planned.criterion_id, planned.allocation.evaluator_id), []
            ).append(planned)
        covered = {
            (criterion_id, evaluator_id)
            for (criterion_id, *_), evaluators in valid_student_evaluators.items()
            for evaluator_id in evaluators
        }
        for (criterion_id, evaluator_id), options in planned_by_evaluator.items():
            if (criterion_id, evaluator_id) in covered:
                continue
            for planned in options:
                allocation = planned.allocation
                key = (criterion_id, *sorted((allocation.left_id, allocation.right_id)))
                evaluators = valid_student_evaluators.setdefault(key, set())
                if evaluator_id in evaluators:
                    continue
                added.append(planned)
                evaluators.add(evaluator_id)
                affected.add(evaluator_id)
                break

    invalid_ids = [pair.id for pair in removed]
    affected_submissions = 0
    if invalid_ids:
        latest_ids = (select(func.max(models.Submission.id))
                      .group_by(models.Submission.student_id, models.Submission.assignment_id,
                                models.Submission.section))
        affected_submissions = db.query(func.count(func.distinct(models.SubmissionChoice.submission_id))).filter(
            models.SubmissionChoice.pair_id.in_(invalid_ids),
            models.SubmissionChoice.submission_id.in_(latest_ids),
        ).scalar() or 0
    return MoveEffects(added, removed, affected, affected_submissions)


def preview_reassignment(db: Session, classroom_id: int, student_id: int,
                         target_group_id: int) -> dict[str, int]:
    student, target, assignments = _validate_move(db, classroom_id, student_id, target_group_id)
    savepoint = db.begin_nested()
    try:
        student.group_id = target.id
        student.group_name = target.name
        db.flush()
        result = _effects_after_move(db, assignments, student.id).summary()
    finally:
        savepoint.rollback()
    return result


def reassign(db: Session, classroom_id: int, student_id: int, target_group_id: int,
             instructor_email: str) -> dict:
    student, target, assignments = _validate_move(db, classroom_id, student_id, target_group_id)
    old_group_id = student.group_id
    now = datetime.now(UTC)
    try:
        student.group_id = target.id
        student.group_name = target.name
        db.flush()
        effects = _effects_after_move(db, assignments, student.id)
        for pair in effects.superseded_pairs:
            pair.superseded_at = now
        for planned in effects.new_pairs:
            allocation = planned.allocation
            db.add(models.Pair(
                assignment_id=db.get(models.Criteria, planned.criterion_id).assignment_id,
                criteria_id=planned.criterion_id, pair_type=allocation.kind,
                assigned_to_student_id=allocation.evaluator_id,
                left_group_id=allocation.left_id if allocation.kind == "group" else None,
                right_group_id=allocation.right_id if allocation.kind == "group" else None,
                left_id=allocation.left_id if allocation.kind == "individual" else None,
                right_id=allocation.right_id if allocation.kind == "individual" else None,
                display_flipped=allocation.flipped,
            ))
        db.add(models.Reassignment(
            classroom_id=classroom_id, student_id=student.id, old_group_id=old_group_id,
            new_group_id=target.id, instructor_email=instructor_email, changed_at=now,
        ))
        db.add_all(models.Notification(
            student_id=affected_id, message="Group membership or pair assignments changed. Review your evaluations.",
            created_at=now,
        ) for affected_id in effects.notified_students)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"student_id": student.id, "old_group_id": old_group_id,
            "new_group_id": target.id, **effects.summary()}
