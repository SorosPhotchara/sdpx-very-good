import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud, models
from app.auth import Identity, current_identity
from app.main import app, get_db
from tests.support import TestDatabase


class ClassroomManagementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = TestDatabase()

        def session():
            with Session(self.database.engine) as db:
                yield db

        app.dependency_overrides[get_db] = session
        self.client = TestClient(app)
        self.sign_in('teacher@example.edu', True)
        self.target = self.populate('Target')
        self.other = self.populate('Other')

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.database.close()

    def sign_in(self, email: str, instructor: bool = False) -> None:
        app.dependency_overrides[current_identity] = lambda: Identity(subject=email, email=email, is_instructor=instructor)

    def populate(self, name: str) -> int:
        room = self.client.post('/classrooms/', json={'name': name}).json()['id']
        now = datetime.now(UTC)
        with Session(self.database.engine) as db:
            groups = [models.Group(classroom_id=room, name=letter) for letter in 'AB']
            db.add_all(groups)
            db.flush()
            students = [models.Student(classroom_id=room, group_id=group.id, email=f'{index}@example.edu') for index, group in enumerate(groups)]
            assignment = models.Assignment(classroom_id=room, title='Review')
            db.add_all([*students, assignment])
            db.flush()
            criterion = models.Criteria(assignment_id=assignment.id, name='Quality', weight=100)
            db.add(criterion)
            db.flush()
            pair = models.Pair(assignment_id=assignment.id, criteria_id=criterion.id, left_id=students[0].id, right_id=students[1].id, assigned_to_student_id=students[0].id)
            submission = models.Submission(assignment_id=assignment.id, student_id=students[0].id, section='individual', submitted_at=now)
            db.add_all([pair, submission])
            db.flush()
            db.add_all([
                models.DraftChoice(student_id=students[0].id, pair_id=pair.id, choice=3),
                models.SubmissionChoice(submission_id=submission.id, pair_id=pair.id, choice=3),
                models.InstructorVote(pair_id=pair.id, choice=3, submitted_at=now),
                models.Notification(student_id=students[0].id, message='Moved', created_at=now),
                models.Reassignment(classroom_id=room, student_id=students[0].id, old_group_id=groups[0].id, new_group_id=groups[1].id, instructor_email='teacher@example.edu', changed_at=now),
            ])
            db.commit()
        return room

    def counts(self) -> dict:
        with Session(self.database.engine) as db:
            return {table.name: db.query(model).count() for model in models.Base.registry.mappers for table in [model.local_table]}

    def test_rename_validates_name_preserves_data_and_instructors(self) -> None:
        before = self.counts()
        path = f'/classrooms/{self.target}'
        self.assertEqual(self.client.patch(path, json={'name': '  '}).status_code, 422)
        response = self.client.patch(path, json={'name': ' Renamed ', 'instructor_emails': 'outsider@example.edu'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'Renamed')
        self.assertEqual(response.json()['instructor_emails'], 'teacher@example.edu')
        self.assertEqual(self.counts(), before)
        self.assertIn('Renamed', [room['name'] for room in self.client.get('/classrooms/').json()])

    def test_only_assigned_instructors_can_rename_or_delete(self) -> None:
        before = self.counts()
        for email, instructor in [('0@example.edu', False), ('outsider@example.edu', True)]:
            self.sign_in(email, instructor)
            self.assertEqual(self.client.patch(f'/classrooms/{self.target}', json={'name': 'Forbidden'}).status_code, 403)
            self.assertEqual(self.client.request('DELETE', f'/classrooms/{self.target}', json={'name': 'Target'}).status_code, 403)
        self.assertEqual(self.counts(), before)

    def test_delete_requires_current_name_removes_dependents_and_preserves_other_room(self) -> None:
        path = f'/classrooms/{self.target}'
        before = self.counts()
        self.assertEqual(self.client.request('DELETE', path, json={'name': 'Wrong'}).status_code, 409)
        self.assertEqual(self.client.request('DELETE', path, json={'name': '  '}).status_code, 422)
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.client.request('DELETE', path, json={'name': 'Target'}).status_code, 204)
        for table, count in self.counts().items():
            self.assertEqual(count, before[table] // 2, table)
        self.assertEqual([room['id'] for room in self.client.get('/classrooms/').json()], [self.other])
        self.assertEqual(self.client.request('DELETE', path, json={'name': 'Target'}).status_code, 404)
        self.assertEqual(self.client.patch(path, json={'name': 'Missing'}).status_code, 404)
        self.sign_in('0@example.edu')
        self.assertEqual(self.client.get('/me').json()['classroom_ids'], [self.other])

    def test_failed_delete_rolls_back_prior_deletions(self) -> None:
        before = self.counts()
        with Session(self.database.engine) as db:
            original = db.execute
            calls = 0

            def fail_after_two_deletes(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 3:
                    raise RuntimeError('Simulated persistence failure')
                return original(*args, **kwargs)

            with patch.object(db, 'execute', side_effect=fail_after_two_deletes):
                with self.assertRaises(RuntimeError):
                    crud.delete_classroom(db, self.target)
        self.assertEqual(self.counts(), before)
