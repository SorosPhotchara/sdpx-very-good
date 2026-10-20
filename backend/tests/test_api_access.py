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

    def test_database_approval_does_not_grant_instructor_access(self) -> None:
        with Session(self.engine) as db:
            db.add(models.InstructorApproval(
                email="outsider@example.edu", approved_by="admin@example.edu",
                approved_at=datetime.now(UTC),
            ))
            db.commit()

        def headers(email: str) -> dict[str, str]:
            return {"Authorization": f"Bearer mock:{email}"}

        with patch.dict("os.environ", {
            "AUTH_MODE": "mock", "APP_ENV": "development",
            "INSTRUCTOR_EMAILS": "teacher@example.edu", "ADMIN_EMAILS": "admin@example.edu",
        }):
            self.assertFalse(self.client.get("/me", headers=headers("outsider@example.edu")).json()["is_instructor"])
            self.assertEqual(self.client.post("/classrooms/", json={"name": "Denied"},
                                              headers=headers("outsider@example.edu")).status_code, 403)
            room = self.client.post("/classrooms/", json={"name": "Allowed"},
                                    headers=headers("teacher@example.edu")).json()["id"]
            self.assertEqual(self.client.post(f"/classrooms/{room}/instructors",
                                              json={"email": "outsider@example.edu"},
                                              headers=headers("teacher@example.edu")).status_code, 422)
            self.assertEqual(self.client.get("/admin/instructors", headers=headers("admin@example.edu")).json(),
                             [{"email": "teacher@example.edu", "source": "environment",
                               "approved_by": None, "approved_at": None}])
            self.assertEqual(self.client.post("/admin/instructors", json={"email": "outsider@example.edu"},
                                              headers=headers("admin@example.edu")).status_code, 409)

    def test_service_prefix_preserves_authentication_and_routes(self) -> None:
        with patch.object(app, "root_path", "/api"):
            self.assertEqual(self.client.get("/api/health").status_code, 200)
            self.assertEqual(self.client.get("/api/me").status_code, 401)
            self.sign_in("teacher@example.edu", is_instructor=True)
            response = self.client.post("/api/classrooms/", json={"name": "Vercel staging"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.client.get("/api/classrooms/").json()[0]["name"], "Vercel staging")

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

    def test_instructor_adds_student_to_group_by_email(self) -> None:
        self.sign_in("teacher@example.edu", is_instructor=True)
        classroom_id = self.client.post("/classrooms/", json={"name": "Course"}).json()["id"]
        response = self.client.post("/students/", json={
            "email": "STUDENT@example.edu", "classroom_id": classroom_id, "group_name": "Team A",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "student@example.edu")
        self.assertEqual(response.json()["group_name"], "Team A")
        self.assertIsNotNone(response.json()["group_id"])
        self.assertEqual(self.client.get("/groups/", params={"classroom_id": classroom_id}).json()[0]["name"], "Team A")
        self.assertEqual(self.client.post("/students/", json={
            "email": "student@example.edu", "classroom_id": classroom_id, "group_name": "Team A",
        }).status_code, 409)
        self.sign_in("student@example.edu")
        self.assertEqual(self.client.get("/me").json()["classroom_ids"], [classroom_id])

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
                "instructor_weight": 2,
                "group_deadline": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                "group_criteria": [{"name": "Quality", "weight": 100}],
            },
        ).json()["id"]
        path = f"/assignments/{assignment_id}"
        setup = self.client.get(path + "/setup").json()
        setup["title"] = "Revised review"
        self.assertEqual(self.client.put(path + "/setup", json=setup).status_code, 200)
        self.assertEqual(self.client.get(path + "/setup").json()["title"], "Revised review")
        self.assertEqual(self.client.get(path + "/preview").json()["pair_assignments"], 9)
        self.assertEqual(self.client.post(path + "/publish").json()["pair_assignments"], 9)
        published = self.client.get("/assignments/", params={"classroom_id": classroom_id}).json()[0]["published_at"]
        self.assertIsNotNone(datetime.fromisoformat(published).tzinfo)
        self.assertEqual(self.client.post(f"/classrooms/{classroom_id}/roster/import", json={
            "csv_text": "email,groupname\nlate@example.edu,Late",
        }).status_code, 409)
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
        self.assertEqual(self.client.post(path + "/instructor-pairs", json={
            "criteria_id": criterion_id, "left_id": groups[1]["id"], "right_id": groups[0]["id"],
            "instructor_email": "TEACHER@example.edu",
        }).status_code, 409)
        self.assertEqual(self.client.put(path + f"/instructor-pairs/{pair_id}/vote", json={"choice": 3}).status_code, 200)
        self.assertEqual(self.client.get(path + "/instructor-pairs").json()[0]["choice"], 3)
        report = self.client.get(path + "/report").json()
        self.assertEqual(len(report["coverage"]), 3)
        self.assertTrue(all({
            "eligible_evaluators": 3, "target_evaluations": 3,
            "assigned_evaluators": 3, "votes": 0,
            "missing_to_target": 3, "shortage_to_target": 2,
        }.items() <= row.items() for row in report["coverage"]))
        instructor_pair = next(row for row in report["coverage"] if {
            row["left_id"], row["right_id"]
        } == {groups[0]["id"], groups[1]["id"]})
        self.assertEqual(instructor_pair["instructor_votes"], 1)
        self.assertEqual(instructor_pair["effective_votes"], 2.0)
        with Session(self.engine) as db:
            flipped = db.get(models.Pair, pair_id).display_flipped
        # Choice 3 is "shown-left slightly better" = 0.6/0.4 on the six-point
        # scale (no tie, D1), scaled by instructor_weight 2. Coverage reports in
        # canonical id order, so the randomised display order (FR-PAIR-08)
        # decides which side carries the larger share.
        self.assertEqual(instructor_pair["left_points"], 0.8 if flipped else 1.2)
        self.assertEqual(instructor_pair["right_points"], 1.2 if flipped else 0.8)
        self.assertTrue(any(row["effective_votes"] > 0 for row in report["criterion_scores"]))

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

    def test_assignment_total_maximum_matches_the_work_sections(self) -> None:
        self.sign_in("teacher@example.edu", is_instructor=True)
        classroom_id = self.client.post("/classrooms/", json={"name": "Course"}).json()["id"]
        deadline = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        setup = {
            "title": "Review", "group_score": 10, "individual_score": 4,
            "total_score": 14, "group_deadline": deadline, "individual_deadline": deadline,
            "group_criteria": [{"name": "Quality", "weight": 100}],
            "individual_criteria": [{"name": "Contribution", "weight": 100}],
        }
        path = f"/classrooms/{classroom_id}/assignments"
        self.assertEqual(self.client.post(path, json={**setup, "total_score": 18}).status_code, 422)
        created = self.client.post(path, json=setup)
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["total_score"], 14)
        assignment_id = created.json()["id"]
        self.assertEqual(self.client.get(f"/assignments/{assignment_id}/setup").json()["total_score"], 14)
        self.assertEqual(self.client.get("/assignments/", params={"classroom_id": classroom_id}).json()[0]["total_score"], 14)
