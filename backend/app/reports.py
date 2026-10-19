"""Compute current work and participation scores from submitted snapshots."""

from datetime import UTC, datetime
from itertools import combinations

from sqlalchemy.orm import Session, selectinload

from . import models
from .scoring import POINTS, PairVote, score_items
from .timezone import as_utc


def assignment_report(db: Session, assignment: models.Assignment) -> dict:
    students = db.query(models.Student).filter_by(classroom_id=assignment.classroom_id).order_by(models.Student.id).all()
    groups = db.query(models.Group).filter_by(classroom_id=assignment.classroom_id).order_by(models.Group.id).all()
    criteria = db.query(models.Criteria).filter_by(assignment_id=assignment.id).all()
    pairs = db.query(models.Pair).filter_by(assignment_id=assignment.id, superseded_at=None).all()
    submissions = (db.query(models.Submission).options(selectinload(models.Submission.choices))
                   .filter_by(assignment_id=assignment.id).order_by(models.Submission.id).all())
    latest = {(item.student_id, item.section): item for item in submissions}
    submitted = {choice.pair_id: choice.choice for item in latest.values() for choice in item.choices}
    instructor_votes = {vote.pair_id: vote.choice for vote in db.query(models.InstructorVote).filter(
        models.InstructorVote.pair_id.in_([pair.id for pair in pairs]))}
    submitted.update(instructor_votes)
    group_members: dict[int, set[int]] = {group.id: set() for group in groups}
    for student in students:
        if student.group_id in group_members:
            group_members[student.group_id].add(student.id)
    active_group_ids = sorted(group_id for group_id, members in group_members.items() if members)

    # Old publications may contain repeated assignments. Only one active answer
    # per evaluator and unordered subject pair may affect a report.
    effective_pairs: dict[tuple, models.Pair] = {}
    for pair in pairs:
        left = pair.left_group_id if pair.pair_type == "group" else pair.left_id
        right = pair.right_group_id if pair.pair_type == "group" else pair.right_id
        if left is None or right is None:
            continue
        key = (pair.criteria_id, *sorted((left, right)),
               "student" if pair.assigned_to_student_id is not None else "instructor",
               pair.assigned_to_student_id or pair.assigned_to_instructor_email)
        previous = effective_pairs.get(key)
        if previous is None or (pair.id in submitted, pair.id) > (previous.id in submitted, previous.id):
            effective_pairs[key] = pair
    pairs = list(effective_pairs.values())
    group_scores: dict[int, float | None] = {group.id: None for group in groups}
    individual_scores: dict[int, float | None] = {student.id: None for student in students}
    # Readable subject labels for the coverage report, matching raw_pair_responses.
    group_labels = {group.id: group.name for group in groups}
    student_labels = {student.id: student.email for student in students}
    coverage = []
    criterion_scores = []

    for criterion in criteria:
        section = "group" if criterion.is_group else "individual"
        deadline = assignment.group_deadline if criterion.is_group else assignment.individual_deadline
        if deadline is not None and deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)
        final = deadline is not None and datetime.now(UTC) >= deadline
        item_ids = [item.id for item in (groups if criterion.is_group else students)]
        eligible_by_pair: dict[tuple[int, int], set[int]] = {}
        if criterion.is_group:
            for left, right in combinations(active_group_ids, 2):
                eligible_by_pair[(left, right)] = {
                    student.id for student in students if student.group_id not in (left, right)
                    and student.group_id in active_group_ids
                }
        else:
            for group_id in active_group_ids:
                members = sorted(group_members[group_id])
                if len(members) < 3:
                    continue
                for left, right in combinations(members, 2):
                    eligible_by_pair[(left, right)] = group_members[group_id] - {left, right}
        criterion_pairs = []
        for pair in pairs:
            if pair.criteria_id != criterion.id or pair.pair_type != section:
                continue
            left = pair.left_group_id if criterion.is_group else pair.left_id
            right = pair.right_group_id if criterion.is_group else pair.right_id
            if left is None or right is None:
                continue
            eligible = eligible_by_pair.get(tuple(sorted((left, right))))
            if eligible is not None and (pair.assigned_to_student_id is None
                                         or pair.assigned_to_student_id in eligible):
                criterion_pairs.append(pair)
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
        assigned_by_pair: dict[tuple[int, int], set[int]] = {key: set() for key in eligible_by_pair}
        votes_by_pair: dict[tuple[int, int], set[int]] = {key: set() for key in eligible_by_pair}
        # [instructor vote count, weighted vote count, left points, right points]
        pair_results: dict[tuple[int, int], list[float]] = {
            key: [0, 0.0, 0.0, 0.0] for key in eligible_by_pair
        }
        for pair in criterion_pairs:
            left = pair.left_group_id if criterion.is_group else pair.left_id
            right = pair.right_group_id if criterion.is_group else pair.right_id
            key = tuple(sorted((left, right)))
            if pair.assigned_to_student_id is not None:
                assigned_by_pair[key].add(pair.assigned_to_student_id)
            if pair.id in submitted:
                weight = assignment.instructor_weight if pair.assigned_to_instructor_email else 1.0
                left_points, right_points = POINTS[submitted[pair.id] - 1]
                if left != key[0]:
                    left_points, right_points = right_points, left_points
                result = pair_results[key]
                result[1] += weight
                result[2] += left_points * weight
                result[3] += right_points * weight
                if pair.assigned_to_student_id is not None:
                    votes_by_pair[key].add(pair.assigned_to_student_id)
                else:
                    result[0] += 1
        labels = group_labels if criterion.is_group else student_labels
        for (left, right), eligible in sorted(eligible_by_pair.items()):
            target_evaluations = min(5, len(eligible))
            count = len(votes_by_pair[(left, right)])
            instructor_count, effective_count, left_points, right_points = pair_results[(left, right)]
            coverage.append({"section": section, "criterion_id": criterion.id, "criterion": criterion.name, "left_id": left,
                             "right_id": right, "left": labels.get(left), "right": labels.get(right),
                             "eligible_evaluators": len(eligible),
                             "target_evaluations": target_evaluations,
                             "assigned_evaluators": len(assigned_by_pair[(left, right)]),
                             "votes": count, "missing_to_target": max(0, target_evaluations - count),
                             "shortage_to_five": 5 - target_evaluations,
                             "instructor_votes": int(instructor_count), "effective_votes": effective_count,
                             "left_points": left_points, "right_points": right_points})

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


def raw_pair_responses(db: Session, assignment: models.Assignment) -> list[dict]:
    """Current assigned pairs and their latest submitted answer for an owner-only report."""
    pairs = db.query(models.Pair).filter_by(assignment_id=assignment.id, superseded_at=None).order_by(models.Pair.id).all()
    submissions = (db.query(models.Submission).options(selectinload(models.Submission.choices))
                   .filter_by(assignment_id=assignment.id).order_by(models.Submission.id).all())
    latest = {(item.student_id, item.section): item for item in submissions}
    answers = {choice.pair_id: (choice.choice, submission.submitted_at)
               for submission in latest.values() for choice in submission.choices}
    answers.update({vote.pair_id: (vote.choice, vote.submitted_at)
                    for vote in db.query(models.InstructorVote).filter(
                        models.InstructorVote.pair_id.in_([pair.id for pair in pairs]))})
    students = {item.id: item.email for item in db.query(models.Student).filter_by(classroom_id=assignment.classroom_id)}
    groups = {item.id: item.name for item in db.query(models.Group).filter_by(classroom_id=assignment.classroom_id)}
    criteria = {item.id: item.name for item in db.query(models.Criteria).filter_by(assignment_id=assignment.id)}
    rows = []
    for pair in pairs:
        is_group = pair.pair_type == "group"
        left_id = pair.left_group_id if is_group else pair.left_id
        right_id = pair.right_group_id if is_group else pair.right_id
        labels = groups if is_group else students
        answer = answers.get(pair.id)
        rows.append({
            "pair_id": pair.id, "section": pair.pair_type,
            "criterion_id": pair.criteria_id, "criterion": criteria[pair.criteria_id],
            "left_id": left_id, "right_id": right_id,
            "left": labels[left_id], "right": labels[right_id],
            "evaluator_student_id": pair.assigned_to_student_id,
            "evaluator": (students[pair.assigned_to_student_id] if pair.assigned_to_student_id is not None
                          else pair.assigned_to_instructor_email),
            "choice": answer[0] if answer else None,
            "submitted_at": as_utc(answer[1]) if answer else None,
        })
    return rows


def _is_final(deadline: datetime | None) -> bool:
    if deadline is None:
        return False
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    return datetime.now(UTC) >= deadline
