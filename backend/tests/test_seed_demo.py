import os
import unittest
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from seed_demo import seed
from tests.support import TestDatabase


class DemoSeedTests(unittest.TestCase):
    def test_seed_is_idempotent_and_publishes_assignment(self) -> None:
        database = TestDatabase()
        try:
            with patch.dict(os.environ, {
                "APP_ENV": "development", "INSTRUCTOR_EMAILS": "teacher@example.edu"
            }):
                seed(database.engine)
                seed(database.engine)
            with Session(database.engine) as session:
                classrooms = session.scalars(select(models.Classroom)).all()
                assignments = session.scalars(select(models.Assignment)).all()
                self.assertEqual(len(classrooms), 5)
                self.assertTrue(all(item.instructor_emails == "teacher@example.edu" for item in classrooms))
                self.assertEqual(session.query(models.Student).count(), 9)
                self.assertEqual(len(assignments), 1)
                self.assertIsNotNone(assignments[0].published_at)
        finally:
            database.close()
