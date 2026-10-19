import unittest

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from tests.support import TestDatabase


class ClassroomTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = TestDatabase()
        self.engine = self.database.engine
        self.db = Session(self.engine)

    def tearDown(self) -> None:
        self.db.close()
        self.database.close()

    def test_create_list_and_serialize_classroom(self) -> None:
        created = crud.create_classroom(
            self.db, schemas.ClassroomCreate(name=" Algorithms ")
        )

        self.assertEqual(created.name, "Algorithms")
        self.assertEqual(crud.get_classrooms(self.db), [created])
        self.assertEqual(
            schemas.Classroom.model_validate(created).model_dump(),
            {"id": created.id, "name": "Algorithms", "instructor_emails": ""},
        )

    def test_blank_name_is_rejected_before_persistence(self) -> None:
        with self.assertRaises(ValidationError):
            schemas.ClassroomCreate(name="   ")

        self.assertEqual(crud.get_classrooms(self.db), [])

    def test_student_can_join_multiple_classrooms_but_not_twice_in_one(self) -> None:
        first = crud.create_classroom(self.db, schemas.ClassroomCreate(name="First"))
        second = crud.create_classroom(self.db, schemas.ClassroomCreate(name="Second"))
        for classroom in (first, second):
            crud.create_student(
                self.db,
                schemas.StudentCreate(email="Student@Example.edu", classroom_id=classroom.id),
            )

        self.assertEqual(crud.get_students(self.db)[0].email, "student@example.edu")

        with self.assertRaises(IntegrityError):
            crud.create_student(
                self.db,
                schemas.StudentCreate(email="student@example.edu", classroom_id=first.id),
            )
