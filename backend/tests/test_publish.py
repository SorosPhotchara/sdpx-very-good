import unittest
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

        self.assertEqual(preview_count, 60)
        self.assertEqual(published_count, preview_count)
        self.assertEqual(len(pairs), preview_count)
        self.assertTrue(all(pair.assigned_to_student_id is not None for pair in pairs))
        with self.assertRaisesRegex(ValueError, "already published"):
            publish(self.db, self.assignment.id)

    def test_invalid_criterion_weight_blocks_publication(self) -> None:
        self.group_criterion.weight = 90
        with self.assertRaisesRegex(ValueError, "100 percent"):
            publish(self.db, self.assignment.id)
        self.assertEqual(self.db.query(models.Pair).count(), 0)
