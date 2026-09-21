import unittest
from unittest.mock import patch
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models
from app.auth import Identity, current_identity
from app.main import app, get_db
from tests.support import TestDatabase


class ApiAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = TestDatabase()
        self.engine = self.database.engine

        def session():
            with Session(self.engine) as db:
                yield db

        app.dependency_overrides[get_db] = session
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.database.close()

    def sign_in(self, email: str, is_instructor: bool = False) -> None:
        app.dependency_overrides[current_identity] = lambda: Identity(
            subject=email, email=email, is_instructor=is_instructor
        )

    def test_health_is_public_but_classrooms_require_sign_in(self) -> None:
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        self.assertEqual(self.client.get("/classrooms/").status_code, 401)
        self.assertEqual(self.client.get("/me").status_code, 401)

    def test_only_approved_instructor_can_create_a_classroom(self) -> None:
        self.sign_in("student@example.edu")
        self.assertEqual(
            self.client.post("/classrooms/", json={"name": "Course"}).status_code,
            403,
        )

        self.sign_in("teacher@example.edu", is_instructor=True)
        self.assertEqual(self.client.get("/me").json()["is_instructor"], True)
        response = self.client.post(
            "/classrooms/",
            json={"name": "Course", "instructor_emails": "attacker@example.edu"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["instructor_emails"], "teacher@example.edu")

    def test_student_sees_only_their_classroom(self) -> None:
        self.sign_in("teacher@example.edu", is_instructor=True)
        classroom_id = self.client.post("/classrooms/", json={"name": "Course"}).json()["id"]
        self.client.post(
            "/students/",
            json={"email": "student@example.edu", "classroom_id": classroom_id},
        )

        self.sign_in("student@example.edu")
        self.assertEqual(self.client.get("/me").json()["classroom_ids"], [classroom_id])
        with Session(self.engine) as db:
            student = db.query(models.Student).filter_by(email="student@example.edu").first()
            self.assertIsNotNone(student.activated_at)
        self.assertEqual(len(self.client.get("/classrooms/").json()), 1)
        self.assertEqual(
            self.client.get("/students/", params={"classroom_id": classroom_id}).status_code,
            403,
        )
        self.sign_in("outsider@example.edu")
        self.assertEqual(self.client.get("/classrooms/").json(), [])

    def test_student_cannot_see_unpublished_assignment(self) -> None:
        self.sign_in("teacher@example.edu", is_instructor=True)
        classroom_id = self.client.post("/classrooms/", json={"name": "Course"}).json()["id"]
        self.client.post("/students/", json={"email": "student@example.edu", "classroom_id": classroom_id})
        assignment_id = self.client.post(f"/classrooms/{classroom_id}/assignments", json={
            "title": "Draft", "group_score": 10,
            "group_deadline": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
            "group_criteria": [{"name": "Quality", "weight": 100}],
        }).json()["id"]
        self.assertEqual(len(self.client.get("/assignments/", params={"classroom_id": classroom_id}).json()), 1)
        self.sign_in("student@example.edu")
        self.assertEqual(self.client.get("/assignments/", params={"classroom_id": classroom_id}).json(), [])
        self.assertEqual(self.client.get(f"/assignments/{assignment_id}/evaluation/group").status_code, 404)
        self.assertEqual(self.client.get(f"/assignments/{assignment_id}/my-scores").status_code, 404)

    def test_one_verified_email_activates_memberships_in_two_classrooms(self) -> None:
        self.sign_in("teacher@example.edu", is_instructor=True)
        classroom_ids = [self.client.post("/classrooms/", json={"name": name}).json()["id"]
                         for name in ("Course A", "Course B")]
        for classroom_id in classroom_ids:
            self.assertEqual(self.client.post("/students/", json={
                "email": "student@example.edu", "classroom_id": classroom_id,
            }).status_code, 200)
        self.sign_in("student@example.edu")
        self.assertEqual(self.client.get("/me").json()["classroom_ids"], classroom_ids)
        self.assertEqual([item["id"] for item in self.client.get("/classrooms/").json()], classroom_ids)
        with Session(self.engine) as db:
            self.assertTrue(all(item.activated_at is not None for item in db.query(models.Student).all()))

    def test_only_owner_can_import_a_roster(self) -> None:
        self.sign_in("teacher@example.edu", is_instructor=True)
        classroom_id = self.client.post("/classrooms/", json={"name": "Course"}).json()["id"]
        self.sign_in("other@example.edu", is_instructor=True)
        path = f"/classrooms/{classroom_id}/roster/import"
        payload = {"csv_text": "email,groupname\nstudent@example.edu,A"}
        self.assertEqual(self.client.post(path, json=payload).status_code, 403)

        self.sign_in("teacher@example.edu", is_instructor=True)
        self.assertEqual(self.client.post(path, json=payload).json()["imported"], 1)
        self.assertEqual(self.client.post(path, json=payload).json()["imported"], 0)

    def test_instructor_invitation_and_removal(self) -> None:
        self.sign_in("teacher@example.edu", is_instructor=True)
        classroom_id = self.client.post("/classrooms/", json={"name": "Course"}).json()["id"]
        path = f"/classrooms/{classroom_id}/instructors"
        with patch.dict("os.environ", {"INSTRUCTOR_EMAILS": "teacher@example.edu,guest@example.edu"}):
            self.assertEqual(self.client.post(path, json={"email": "unknown@example.edu"}).status_code, 422)
            self.assertEqual(self.client.post(path, json={"email": "guest@example.edu"}).status_code, 200)
            self.sign_in("guest@example.edu", is_instructor=True)
            self.assertEqual(len(self.client.get("/classrooms/").json()), 1)
            self.assertEqual(self.client.delete(path + "/teacher@example.edu").status_code, 200)
            self.assertEqual(self.client.delete(path + "/guest@example.edu").status_code, 409)
            self.sign_in("teacher@example.edu", is_instructor=True)
            self.assertEqual(self.client.get("/classrooms/").json(), [])

    def test_other_classroom_instructor_cannot_read_setup_or_report(self) -> None:
        self.sign_in("teacher@example.edu", is_instructor=True)
        classroom_id = self.client.post("/classrooms/", json={"name": "Private"}).json()["id"]
        assignment_id = self.client.post(f"/classrooms/{classroom_id}/assignments", json={
            "title": "Private draft", "group_score": 10,
            "group_deadline": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
            "group_criteria": [{"name": "Quality", "weight": 100}],
        }).json()["id"]
        self.sign_in("other@example.edu", is_instructor=True)
        self.assertEqual(self.client.get(f"/assignments/{assignment_id}/setup").status_code, 403)
        self.assertEqual(self.client.get(f"/assignments/{assignment_id}/report").status_code, 403)
        self.assertEqual(self.client.get(f"/assignments/{assignment_id}/report.xlsx").status_code, 403)

    def test_owner_can_preview_and_publish_eligible_pairs(self) -> None:
        self.sign_in("teacher@example.edu", is_instructor=True)
        classroom_id = self.client.post("/classrooms/", json={"name": "Course"}).json()["id"]
        roster = "email,groupname\n" + "\n".join(
            f"student{group}{number}@example.edu,{group}"
            for group in "ABC"
            for number in range(3)
        )
        self.assertEqual(
            self.client.post(
                f"/classrooms/{classroom_id}/roster/import", json={"csv_text": roster}
            ).json()["imported"],
            9,
        )
        assignment_id = self.client.post(
            f"/classrooms/{classroom_id}/assignments",
            json={
                "title": "Review",
                "group_score": 10,
                "group_deadline": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                "group_criteria": [{"name": "Quality", "weight": 100}],
            },
        ).json()["id"]
        path = f"/assignments/{assignment_id}"
        setup = self.client.get(path + "/setup").json()
        setup["title"] = "Revised review"
        self.assertEqual(self.client.put(path + "/setup", json=setup).status_code, 200)
        self.assertEqual(self.client.get(path + "/setup").json()["title"], "Revised review")
        self.assertEqual(self.client.get(path + "/preview").json()["pair_assignments"], 15)
        self.assertEqual(self.client.post(path + "/publish").json()["pair_assignments"], 15)
        published = self.client.get("/assignments/", params={"classroom_id": classroom_id}).json()[0]["published_at"]
        self.assertIsNotNone(datetime.fromisoformat(published).tzinfo)
        self.assertEqual(self.client.post(path + "/publish").status_code, 422)
        self.assertEqual(self.client.put(path + "/setup", json=setup).status_code, 422)

        criterion_id = self.client.get(path + "/criteria").json()[0]["id"]
        groups = self.client.get("/groups/", params={"classroom_id": classroom_id}).json()
        extra = self.client.post(path + "/instructor-pairs", json={
            "criteria_id": criterion_id, "left_id": groups[0]["id"], "right_id": groups[1]["id"],
            "instructor_email": "teacher@example.edu",
        })
        self.assertEqual(extra.status_code, 200)
        pair_id = extra.json()["pair_id"]
        self.assertEqual(self.client.put(path + f"/instructor-pairs/{pair_id}/vote", json={"choice": 3}).status_code, 200)
        self.assertEqual(self.client.get(path + "/instructor-pairs").json()[0]["choice"], 3)
        self.assertEqual(self.client.get(path + "/report").json()["coverage"][0]["votes"], 1)

        self.sign_in("studentA0@example.edu")
        self.assertEqual(self.client.get(path + "/preview").status_code, 403)

    def test_invalid_assignment_is_not_partially_created(self) -> None:
        self.sign_in("teacher@example.edu", is_instructor=True)
        classroom_id = self.client.post("/classrooms/", json={"name": "Course"}).json()["id"]
        response = self.client.post(
            f"/classrooms/{classroom_id}/assignments",
            json={
                "title": "Review",
                "group_score": 10,
                "group_deadline": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                "group_criteria": [{"name": "Quality", "weight": 90}],
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            self.client.get("/assignments/", params={"classroom_id": classroom_id}).json(),
            [],
        )
