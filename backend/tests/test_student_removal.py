import unittest
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models
from app.auth import Identity, current_identity
from app.main import app, get_db
from tests.support import TestDatabase


class StudentRemovalTests(unittest.TestCase):
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
        """A roster with no evaluation anywhere, which is when removal is allowed."""
        room = self.client.post('/classrooms/', json={'name': name}).json()['id']
        with Session(self.database.engine) as db:
            groups = [models.Group(classroom_id=room, name=letter) for letter in 'AB']
            db.add_all(groups)
            db.flush()
            db.add_all([
                models.Student(classroom_id=room, group_id=groups[index % 2].id,
                               group_name=groups[index % 2].name,
                               email=f'{name.lower()}{index}@example.edu')
                for index in range(3)
            ])
            db.commit()
        return room

    def counts(self) -> dict:
        with Session(self.database.engine) as db:
            return {table.name: db.query(model).count()
                    for model in models.Base.registry.mappers for table in [model.local_table]}

    def roster(self, room: int) -> list[dict]:
        return self.client.get('/students/', params={'classroom_id': room, 'limit': 500}).json()

    def path(self, room: int, student_id: int) -> str:
        return f'/classrooms/{room}/students/{student_id}'

    def test_removal_requires_the_current_email_and_removes_only_that_membership(self) -> None:
        students = self.roster(self.target)
        victim = students[0]
        before = self.counts()

        path = self.path(self.target, victim['id'])
        self.assertEqual(self.client.request('DELETE', path, json={'email': 'wrong@example.edu'}).status_code, 409)
        self.assertEqual(self.client.request('DELETE', path, json={'email': '   '}).status_code, 422)
        self.assertEqual(self.counts(), before)

        self.assertEqual(self.client.request('DELETE', path, json={'email': victim['email'].upper()}).status_code, 204)
        self.assertEqual(self.counts()['students'], before['students'] - 1)
        self.assertEqual(
            sorted(student['email'] for student in self.roster(self.target)),
            sorted(student['email'] for student in students[1:]),
        )
        self.assertEqual(len(self.roster(self.other)), 3)
        self.assertEqual(self.client.request('DELETE', path, json={'email': victim['email']}).status_code, 404)

        self.sign_in(victim['email'])
        self.assertEqual(self.client.get('/me').json()['classroom_ids'], [])

    def test_removal_is_blocked_once_an_evaluation_exists(self) -> None:
        students = self.roster(self.target)
        path = self.path(self.target, students[0]['id'])
        payload = {'email': students[0]['email']}
        now = datetime.now(UTC)

        with Session(self.database.engine) as db:
            assignment = models.Assignment(classroom_id=self.target, title='Review', published_at=now)
            db.add(assignment)
            db.flush()
            criterion = models.Criteria(assignment_id=assignment.id, name='Quality', weight=100)
            db.add(criterion)
            db.commit()
            assignment_id, criterion_id = assignment.id, criterion.id
        before = self.counts()
        self.assertEqual(self.client.request('DELETE', path, json=payload).status_code, 409)
        self.assertEqual(self.counts(), before)

        # An instructor-assigned pair never sets published_at, so the publication flag
        # alone would let this through and orphan the foreign keys of a live pair.
        with Session(self.database.engine) as db:
            db.get(models.Assignment, assignment_id).published_at = None
            db.add(models.Pair(assignment_id=assignment_id, criteria_id=criterion_id,
                               left_id=students[1]['id'], right_id=students[2]['id'],
                               assigned_to_student_id=students[0]['id'], pair_type='individual'))
            db.commit()
        before = self.counts()
        self.assertEqual(self.client.request('DELETE', path, json=payload).status_code, 409)
        self.assertEqual(self.counts(), before)

        with Session(self.database.engine) as db:
            db.query(models.Pair).delete()
            db.commit()
        self.assertEqual(self.client.request('DELETE', path, json=payload).status_code, 204)

    def test_only_assigned_instructors_can_remove_students(self) -> None:
        students = self.roster(self.target)
        path = self.path(self.target, students[0]['id'])
        payload = {'email': students[0]['email']}
        before = self.counts()

        for email, instructor in ((students[1]['email'], False), ('stranger@example.edu', True)):
            self.sign_in(email, instructor)
            self.assertEqual(self.client.request('DELETE', path, json=payload).status_code, 403)
            self.assertEqual(self.counts(), before)

        self.sign_in('teacher@example.edu', True)
        self.assertEqual(
            self.client.request('DELETE', self.path(self.other, students[0]['id']), json=payload).status_code,
            404,
        )
        self.assertEqual(self.counts(), before)

    def test_removal_deletes_that_members_notifications_and_audit_rows_only(self) -> None:
        students = self.roster(self.target)
        now = datetime.now(UTC)
        with Session(self.database.engine) as db:
            groups = db.query(models.Group).filter_by(classroom_id=self.target).order_by(models.Group.id).all()
            for student in students[:2]:
                db.add_all([
                    models.Notification(student_id=student['id'], message='Moved', created_at=now),
                    models.Reassignment(classroom_id=self.target, student_id=student['id'],
                                        old_group_id=groups[0].id, new_group_id=groups[1].id,
                                        instructor_email='teacher@example.edu', changed_at=now),
                ])
            db.commit()

        # Drafts and submissions both need a pair, which the guard already forbids, so
        # these two tables are everything a pre-evaluation member can leave behind.
        path = self.path(self.target, students[0]['id'])
        self.assertEqual(self.client.request('DELETE', path, json={'email': students[0]['email']}).status_code, 204)
        with Session(self.database.engine) as db:
            self.assertEqual(db.query(models.Notification).filter_by(student_id=students[0]['id']).count(), 0)
            self.assertEqual(db.query(models.Reassignment).filter_by(student_id=students[0]['id']).count(), 0)
            self.assertEqual(db.query(models.Notification).filter_by(student_id=students[1]['id']).count(), 1)
            self.assertEqual(db.query(models.Reassignment).filter_by(student_id=students[1]['id']).count(), 1)

    def test_removing_the_last_member_keeps_the_group_and_reopens_import(self) -> None:
        for student in self.roster(self.target):
            self.assertEqual(
                self.client.request('DELETE', self.path(self.target, student['id']),
                                    json={'email': student['email']}).status_code,
                204,
            )

        self.assertEqual(self.roster(self.target), [])
        groups = self.client.get('/groups/', params={'classroom_id': self.target}).json()
        self.assertEqual(sorted(group['name'] for group in groups), ['A', 'B'])

        imported = self.client.post(f'/classrooms/{self.target}/roster/import',
                                    json={'csv_text': 'email,groupname\nfresh@example.edu,A'})
        self.assertEqual(imported.json(), {'imported': 1, 'errors': []})
        self.assertEqual(
            len(self.client.get('/groups/', params={'classroom_id': self.target}).json()),
            len(groups),
        )
