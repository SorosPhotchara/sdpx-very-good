import unittest
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app import models
from app.publish import build_plan, publish
from tests.support import TestDatabase


class PublishTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = TestDatabase()
        self.engine = self.database.engine
        self.db = Session(self.engine)
        classroom = models.Classroom(name="Course", instructor_emails="teacher@example.edu")
        self.db.add(classroom)
        self.db.flush()
        for group_number in range(3):
            group = models.Group(name=f"Group {group_number}", classroom_id=classroom.id)
            self.db.add(group)
            self.db.flush()
            for student_number in range(3):
                self.db.add(models.Student(
                    email=f"student{group_number}{student_number}@example.edu",
                    classroom_id=classroom.id,
                    group_id=group.id,
                ))
        self.assignment = models.Assignment(
            title="Review", classroom_id=classroom.id, group_score=20, individual_score=10,
            group_deadline=datetime.now(UTC) + timedelta(days=7),
            individual_deadline=datetime.now(UTC) + timedelta(days=7),
        )
        self.db.add(self.assignment)
        self.db.flush()
        self.group_criterion = models.Criteria(
            assignment_id=self.assignment.id, name="Quality", weight=100, is_group=True
        )
        self.individual_criterion = models.Criteria(
            assignment_id=self.assignment.id, name="Contribution", weight=100, is_group=False
        )
        self.db.add_all([self.group_criterion, self.individual_criterion])
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.database.close()

    def test_preview_and_publish_have_same_count_and_persist_evaluators(self) -> None:
        preview_count = len(build_plan(self.db, self.assignment.id))
        published_count = publish(self.db, self.assignment.id)
        pairs = self.db.query(models.Pair).all()

        self.assertEqual(preview_count, 18)
        self.assertEqual(published_count, preview_count)
        self.assertEqual(len(pairs), preview_count)
        self.assertTrue(all(pair.assigned_to_student_id is not None for pair in pairs))
        self.assertEqual(len(pairs), len({
            (pair.criteria_id, pair.left_group_id or pair.left_id,
             pair.right_group_id or pair.right_id, pair.assigned_to_student_id)
            for pair in pairs
        }))
        with self.assertRaisesRegex(ValueError, "already published"):
            publish(self.db, self.assignment.id)

    def test_invalid_criterion_weight_blocks_publication(self) -> None:
        self.group_criterion.weight = 90
        with self.assertRaisesRegex(ValueError, "100 percent"):
            publish(self.db, self.assignment.id)
        self.assertEqual(self.db.query(models.Pair).count(), 0)

    def test_group_workload_stays_balanced_across_criteria(self) -> None:
        groups = self.db.query(models.Group).order_by(models.Group.id).all()
        for group, target_size in zip(groups, (8, 9, 8), strict=True):
            for student_number in range(3, target_size):
                self.db.add(models.Student(
                    email=f"extra-{group.id}-{student_number}@example.edu",
                    classroom_id=group.classroom_id,
                    group_id=group.id,
                ))

        self.db.delete(self.group_criterion)
        self.db.delete(self.individual_criterion)
        self.assignment.individual_score = 0
        self.assignment.individual_deadline = None
        self.db.flush()
        self.db.add_all([
            models.Criteria(
                id=10, assignment_id=self.assignment.id,
                name="Quality", weight=50, is_group=True,
            ),
            models.Criteria(
                id=11, assignment_id=self.assignment.id,
                name="Completeness", weight=50, is_group=True,
            ),
        ])
        self.db.commit()

        plan = build_plan(self.db, self.assignment.id)
        loads = Counter(
            item.allocation.evaluator_id
            for item in plan
            if item.allocation.kind == "group"
        )

        for group in groups:
            group_loads = [loads[student.id] for student in group.students]
            self.assertGreaterEqual(min(group_loads), 1)
            self.assertLessEqual(max(group_loads) - min(group_loads), 1)

    def test_every_student_evaluates_in_every_group_criterion(self) -> None:
        groups = self.db.query(models.Group).order_by(models.Group.id).all()
        for group in groups:
            for student_number in range(3, 10):
                self.db.add(models.Student(
                    email=f"extra-{group.id}-{student_number}@example.edu",
                    classroom_id=group.classroom_id,
                    group_id=group.id,
                ))

        self.db.delete(self.group_criterion)
        self.db.delete(self.individual_criterion)
        self.assignment.individual_score = 0
        self.assignment.individual_deadline = None
        self.db.flush()
        self.db.add_all([
            models.Criteria(
                id=10, assignment_id=self.assignment.id,
                name="Quality", weight=50, is_group=True,
            ),
            models.Criteria(
                id=11, assignment_id=self.assignment.id,
                name="Completeness", weight=50, is_group=True,
            ),
        ])
        self.db.commit()

        plan = build_plan(self.db, self.assignment.id)
        per_criterion: dict[int, Counter[int]] = {}
        for item in plan:
            per_criterion.setdefault(item.criterion_id, Counter())[item.allocation.evaluator_id] += 1

        # Thirty students across three groups leave only fifteen coverage slots per
        # criterion, so the floor is what keeps anyone from opening an empty section.
        self.assertEqual(len(per_criterion), 2)
        for counts in per_criterion.values():
            self.assertEqual(len(counts), 30)
            self.assertEqual(set(counts.values()), {1})
        self.assertEqual(publish(self.db, self.assignment.id), len(plan))
        pairs = self.db.query(models.Pair).filter_by(superseded_at=None).all()
        self.assertEqual(len({
            (pair.criteria_id, pair.assigned_to_student_id) for pair in pairs
        }), 60)
