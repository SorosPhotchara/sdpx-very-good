import unittest
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models
from app.auth import Identity, current_identity
from app.main import app, get_db
from tests.support import TestDatabase


class EvaluationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = TestDatabase()
        self.engine = self.database.engine

        def session():
            with Session(self.engine) as db:
                yield db

        app.dependency_overrides[get_db] = session
        self.client = TestClient(app)
        self.sign_in("teacher@example.edu", True)
        classroom_id = self.client.post("/classrooms/", json={"name": "Course"}).json()["id"]
        roster = "email,groupname\n" + "\n".join(f"{group}{index}@example.edu,{group}" for group in "ABC" for index in range(3))
        self.assertEqual(self.client.post(f"/classrooms/{classroom_id}/roster/import", json={"csv_text": roster}).json()["imported"], 9)
        self.assignment_id = self.client.post(f"/classrooms/{classroom_id}/assignments", json={
            "title": "Review", "group_score": 10, "group_participation_max": 5,
            "group_deadline": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
            "group_criteria": [{"name": "Quality", "weight": 100}],
        }).json()["id"]
        self.client.post(f"/assignments/{self.assignment_id}/publish")
        with Session(self.engine) as db:
            pair = db.query(models.Pair).first()
            student = db.get(models.Student, pair.assigned_to_student_id)
            self.email = student.email
            self.pair_id = pair.id
            self.other_pair_id = db.query(models.Pair.id).filter(
                models.Pair.assigned_to_student_id != student.id).first()[0]
        self.path = f"/assignments/{self.assignment_id}/evaluation/group"

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.database.close()

    def sign_in(self, email: str, instructor: bool = False) -> None:
        app.dependency_overrides[current_identity] = lambda: Identity(subject=email, email=email, is_instructor=instructor)

    def test_draft_submit_and_latest_snapshot(self) -> None:
        self.sign_in(self.email)
        page = self.client.get(self.path)
        self.assertEqual(page.status_code, 200)
        self.assertTrue(page.json()["is_open"])
        self.assertIsNone(page.json()["pairs"][0]["submitted_choice"])
        self.assertEqual(self.client.post(self.path + "/submit").status_code, 422)

        payload = {"changes": [{"pair_id": self.pair_id, "choice": 1}]}
        self.assertEqual(self.client.put(self.path + "/draft", json=payload).status_code, 200)
        first = self.client.post(self.path + "/submit").json()
        self.assertEqual(first["answered"], 1)
        self.assertIsNotNone(datetime.fromisoformat(self.client.get(self.path).json()["submitted_at"]).tzinfo)
        self.assertEqual(self.client.get(self.path).json()["pairs"][0]["submitted_choice"], 1)

        payload["changes"][0]["choice"] = 5
        self.client.put(self.path + "/draft", json=payload)
        self.assertEqual(self.client.get(self.path).json()["pairs"][0]["submitted_choice"], 1)
        second = self.client.post(self.path + "/submit").json()
        self.assertNotEqual(first["submission_id"], second["submission_id"])
        self.assertEqual(self.client.get(self.path).json()["pairs"][0]["submitted_choice"], 5)
        with Session(self.engine) as db:
            snapshots = db.query(models.SubmissionChoice).filter_by(pair_id=self.pair_id).order_by(models.SubmissionChoice.id).all()
            self.assertEqual([item.choice for item in snapshots], [1, 5])

    def test_access_and_expired_deadline(self) -> None:
        self.sign_in("outsider@example.edu")
        self.assertEqual(self.client.get(self.path).status_code, 403)
        self.sign_in(self.email)
        self.assertEqual(self.client.put(self.path + "/draft", json={"changes": [{"pair_id": self.pair_id, "choice": 6}]}).status_code, 422)
        with Session(self.engine) as db:
            assignment = db.get(models.Assignment, self.assignment_id)
            assignment.group_deadline = datetime.now(UTC) - timedelta(minutes=1)
            db.commit()
        self.assertFalse(self.client.get(self.path).json()["is_open"])
        self.assertEqual(self.client.put(self.path + "/draft", json={"changes": [{"pair_id": self.pair_id, "choice": 1}]}).status_code, 409)
        self.assertEqual(self.client.post(self.path + "/submit").status_code, 409)

    def test_invalid_draft_batch_does_not_replace_saved_answer(self) -> None:
        self.sign_in(self.email)
        self.assertEqual(self.client.put(self.path + "/draft", json={
            "changes": [{"pair_id": self.pair_id, "choice": 2}],
        }).status_code, 200)
        response = self.client.put(self.path + "/draft", json={"changes": [
            {"pair_id": self.pair_id, "choice": 5},
            {"pair_id": self.other_pair_id, "choice": 1},
        ]})
        self.assertEqual(response.status_code, 422)
        choices = {item["id"]: item["draft_choice"] for item in self.client.get(self.path).json()["pairs"]}
        self.assertEqual(choices[self.pair_id], 2)

    def test_report_uses_submitted_answers_and_hides_peers(self) -> None:
        self.sign_in(self.email)
        self.assertEqual(self.client.get(f"/assignments/{self.assignment_id}/report").status_code, 403)
        self.assertEqual(self.client.get(f"/assignments/{self.assignment_id}/report/pairs.csv").status_code, 403)
        self.assertEqual(self.client.get(f"/assignments/{self.assignment_id}/report.xlsx").status_code, 403)
        before = self.client.get(f"/assignments/{self.assignment_id}/my-scores").json()
        self.assertIsNone(before["group_work_score"])
        self.client.put(self.path + "/draft", json={"changes": [{"pair_id": self.pair_id, "choice": 1}]})
        self.assertIsNone(self.client.get(f"/assignments/{self.assignment_id}/my-scores").json()["group_work_score"])
        self.client.post(self.path + "/submit")
        after = self.client.get(f"/assignments/{self.assignment_id}/my-scores").json()
        self.assertIsNone(after["group_work_score"])
        self.assertGreater(after["group_participation_score"], 0)
        self.assertNotIn("students", after)
        self.sign_in("teacher@example.edu", True)
        report = self.client.get(f"/assignments/{self.assignment_id}/report").json()
        self.assertEqual(len(report["students"]), 9)
        self.assertTrue(any(group["work_score"] is not None for group in report["groups"]))
        self.assertTrue(any(row["votes"] == 1 for row in report["coverage"]))
        exported = self.client.get(f"/assignments/{self.assignment_id}/report/pairs.csv")
        self.assertEqual(exported.status_code, 200)
        self.assertIn("Evaluator 1", exported.text)
        self.assertNotIn(self.email, exported.text)

    def test_reassignment_preserves_eligible_pairs_and_records_notifications(self) -> None:
        with Session(self.engine) as db:
            student = db.query(models.Student).filter_by(email="a0@example.edu").first()
            target = db.query(models.Group).filter_by(name="B").first()
            student_id, target_id = student.id, target.id
        self.sign_in("teacher@example.edu", True)
        path = f"/classrooms/1/students/{student_id}/group"
        response = self.client.put(path, json={"group_id": target_id})
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.json()["changed_pairs"], 0)
        self.assertEqual(len(self.client.get("/classrooms/1/reassignments").json()), 1)
        report = self.client.get(f"/assignments/{self.assignment_id}/report").json()
        self.assertTrue(all(item["votes"] == 0 for item in report["coverage"]))
        with Session(self.engine) as db:
            self.assertTrue(db.query(models.Pair).filter(models.Pair.superseded_at.is_not(None)).first())
            self.assertEqual(db.query(models.Pair).filter_by(assignment_id=self.assignment_id, superseded_at=None).count(), 15)
        self.sign_in("a0@example.edu")
        self.assertTrue(self.client.get("/classrooms/1/notifications").json())
        self.assertEqual(self.client.put(path, json={"group_id": target_id}).status_code, 403)
