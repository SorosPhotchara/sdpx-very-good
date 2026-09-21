import unittest

from sqlalchemy.orm import Session

from app import models
from app.roster import import_roster, parse_roster
from tests.support import TestDatabase


class RosterTests(unittest.TestCase):
    def test_quoted_group_and_header_variants_are_accepted(self) -> None:
        result = parse_roster('\ufeffEmail,Group Name\nStudent@Example.edu,"Design, A"')
        self.assertEqual(result.errors, [])
        self.assertEqual(result.rows[0].email, "student@example.edu")
        self.assertEqual(result.rows[0].group_name, "Design, A")

    def test_invalid_and_duplicate_rows_reject_the_whole_import(self) -> None:
        result = parse_roster(
            "email,groupname\nstudent@example.edu,A\nSTUDENT@example.edu,B\ninvalid,=SUM(1)"
        )
        self.assertEqual(result.rows, [])
        self.assertIn("Row 3: duplicate email", result.errors)
        self.assertIn("Row 4: invalid email", result.errors)

    def test_import_creates_groups_and_students_atomically(self) -> None:
        database = TestDatabase()
        with Session(database.engine) as db:
            classroom = models.Classroom(name="Course")
            db.add(classroom)
            db.commit()
            result = import_roster(
                db,
                classroom.id,
                "email,groupname\na@example.edu,A\nb@example.edu,A\nc@example.edu,B",
            )
            self.assertEqual(len(result.rows), 3)
            self.assertEqual(db.query(models.Group).count(), 2)
            self.assertEqual(db.query(models.Student).count(), 3)
            rejected = import_roster(db, classroom.id, "email,groupname\nx@example.edu,C")
            self.assertTrue(rejected.errors)
            self.assertEqual(db.query(models.Student).count(), 3)
        database.close()
