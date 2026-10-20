"""The assignment state machine of PRD §7.3 and the finalize snapshot."""

import unittest
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models
from app.auth import Identity, current_identity
from app.lifecycle import DRAFT, FINALIZED, PUBLISHED, is_final
from app.main import app, get_db
from tests.support import TestDatabase

TEACHER = "teacher@example.edu"


class LifecycleApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = TestDatabase()
        self.engine = self.database.engine

        def session():
            with Session(self.engine) as db:
                yield db

        app.dependency_overrides[get_db] = session
        self.client = TestClient(app)
        self.sign_in(TEACHER, True)
        self.classroom_id = self.client.post("/classrooms/", json={"name": "Course"}).json()["id"]
        roster = "email,groupname\n" + "\n".join(
            f"{group}{index}@example.edu,{group}"
            for group, size in {"A": 3, "B": 3, "C": 3}.items() for index in range(size))
        self.client.post(f"/classrooms/{self.classroom_id}/roster/import",
                         json={"csv_text": roster})
        self.assignment_id = self.client.post(
            f"/classrooms/{self.classroom_id}/assignments", json={
                "title": "Review", "group_score": 10,
                "group_deadline": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                "group_criteria": [{"name": "Quality", "weight": 100}],
            }).json()["id"]
        self.path = f"/assignments/{self.assignment_id}"

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()
        self.database.close()

    def sign_in(self, email: str, instructor: bool = False) -> None:
        app.dependency_overrides[current_identity] = lambda: Identity(
            subject=email, email=email, is_instructor=instructor)

    def status(self) -> str:
        with Session(self.engine) as db:
            return db.get(models.Assignment, self.assignment_id).status

    def test_a_new_assignment_is_a_draft_until_published(self) -> None:
        self.assertEqual(self.status(), DRAFT)
        self.assertEqual(self.client.post(self.path + "/publish").status_code, 200)
        self.assertEqual(self.status(), PUBLISHED)

    def test_unpublish_needs_a_reason_and_withdraws_the_pairs(self) -> None:
        self.client.post(self.path + "/publish")
        with Session(self.engine) as db:
            active = db.query(models.Pair).filter_by(
                assignment_id=self.assignment_id, superseded_at=None).count()
        self.assertGreater(active, 0)

        refused = self.client.post(self.path + "/unpublish", json={})
        self.assertEqual(refused.status_code, 409)
        self.assertIn("reason", refused.json()["detail"].lower())
        self.assertEqual(self.status(), PUBLISHED)

        done = self.client.post(self.path + "/unpublish",
                                json={"reason": "criteria were wrong"})
        self.assertEqual(done.status_code, 200)
        self.assertEqual(done.json()["withdrawn_pairs"], active)
        self.assertEqual(self.status(), DRAFT)
        with Session(self.engine) as db:
            self.assertEqual(db.query(models.Pair).filter_by(
                assignment_id=self.assignment_id).count(), 0)
            # DR-02: the plan leaves the operational tables but not the database.
            event = (db.query(models.AssignmentEvent)
                     .filter_by(assignment_id=self.assignment_id, action="unpublish").one())
            self.assertEqual(len(event.snapshot["pairs"]), active)
            self.assertEqual(event.reason, "criteria were wrong")

    def test_a_draft_can_be_edited_again_after_unpublishing(self) -> None:
        self.client.post(self.path + "/publish")
        setup = self.client.get(self.path + "/setup").json()
        self.assertEqual(self.client.put(self.path + "/setup", json=setup).status_code, 422)

        self.client.post(self.path + "/unpublish", json={"reason": "fixing the weights"})
        self.assertEqual(self.client.put(self.path + "/setup", json=setup).status_code, 200)

    def test_a_submitted_answer_survives_unpublish_and_republish(self) -> None:
        self.client.post(self.path + "/publish")
        with Session(self.engine) as db:
            pair = db.query(models.Pair).filter_by(assignment_id=self.assignment_id).first()
            evaluator = db.get(models.Student, pair.assigned_to_student_id).email
            pair_id = pair.id
        self.sign_in(evaluator)
        page = f"{self.path}/evaluation/group"
        self.assertEqual(self.client.put(page + "/draft", json={
            "changes": [{"pair_id": pair_id, "choice": 2}]}).status_code, 200)
        self.assertEqual(self.client.post(page + "/submit").status_code, 200)

        self.sign_in(TEACHER, True)
        withdrawn = self.client.post(self.path + "/unpublish",
                                     json={"reason": "a criterion was ambiguous"}).json()
        self.assertEqual(withdrawn["withdrawn_answers"], 1)
        with Session(self.engine) as db:
            # Nothing of it is left live, and all of it is on the event.
            self.assertEqual(db.query(models.Submission).filter_by(
                assignment_id=self.assignment_id).count(), 0)
            event = (db.query(models.AssignmentEvent)
                     .filter_by(assignment_id=self.assignment_id, action="unpublish").one())
            self.assertEqual([item["choice"] for item in event.snapshot["submission_choices"]], [2])

        # And the assignment can be edited and published again (FR-PAIR-11).
        setup = self.client.get(self.path + "/setup").json()
        setup["group_criteria"] = [{"name": "Clarity", "weight": 100}]
        self.assertEqual(self.client.put(self.path + "/setup", json=setup).status_code, 200)
        republished = self.client.post(self.path + "/publish")
        self.assertEqual(republished.status_code, 200)
        self.assertGreater(republished.json()["pair_assignments"], 0)
        self.assertEqual(self.status(), PUBLISHED)

    def test_finalize_snapshots_the_calculation_and_locks_recompute(self) -> None:
        self.client.post(self.path + "/publish")
        finalized = self.client.post(self.path + "/finalize")
        self.assertEqual(finalized.status_code, 200)
        self.assertEqual(finalized.json()["status"], FINALIZED)
        self.assertIsNotNone(finalized.json()["finalized_at"])

        # FR-SCORE-09: inputs and outputs are both kept.
        with Session(self.engine) as db:
            event = db.get(models.AssignmentEvent, finalized.json()["event_id"])
            self.assertEqual(event.action, "finalize")
            self.assertEqual(event.actor_email, TEACHER)
            self.assertEqual(set(event.snapshot), {"formula", "report"})
            self.assertEqual(event.snapshot["formula"]["score_floor"], 0.6)
            self.assertEqual(event.snapshot["formula"]["completion_threshold"], 0.9)
            self.assertIn("students", event.snapshot["report"])

        # Both sections read as settled even though the deadline has not passed.
        report = self.client.get(self.path + "/report").json()
        self.assertEqual(report["status"], FINALIZED)
        self.assertTrue(report["group_final"])
        self.assertTrue(report["individual_final"])

        self.assertEqual(self.client.post(self.path + "/recompute").status_code, 409)
        self.assertEqual(self.client.post(self.path + "/finalize").status_code, 409)

    def test_reopen_needs_a_reason_and_clears_the_finalized_mark(self) -> None:
        self.client.post(self.path + "/publish")
        self.client.post(self.path + "/finalize")

        self.assertEqual(self.client.post(self.path + "/reopen", json={}).status_code, 409)
        self.assertEqual(self.status(), FINALIZED)

        reopened = self.client.post(self.path + "/reopen",
                                    json={"reason": "a grade was appealed"})
        self.assertEqual(reopened.status_code, 200)
        self.assertEqual(self.status(), PUBLISHED)
        with Session(self.engine) as db:
            self.assertIsNone(db.get(models.Assignment, self.assignment_id).finalized_at)
        self.assertFalse(self.client.get(self.path + "/report").json()["group_final"])

    def test_forbidden_transitions_are_refused(self) -> None:
        # A draft cannot be finalized or unpublished.
        self.assertEqual(self.client.post(self.path + "/finalize").status_code, 409)
        self.assertEqual(self.client.post(self.path + "/unpublish",
                                          json={"reason": "no"}).status_code, 409)
        self.assertEqual(self.status(), DRAFT)

    def test_events_record_who_did_what_and_why(self) -> None:
        self.client.post(self.path + "/publish")
        self.client.post(self.path + "/recompute")
        self.client.post(self.path + "/finalize")
        self.client.post(self.path + "/reopen", json={"reason": "appeal upheld"})

        events = self.client.get(self.path + "/events").json()
        self.assertEqual([event["action"] for event in events],
                         ["reopen", "finalize", "recompute"])
        self.assertEqual({event["actor"] for event in events}, {TEACHER})
        self.assertEqual(events[0]["reason"], "appeal upheld")
        self.assertTrue(events[1]["has_snapshot"])
        self.assertFalse(events[2]["has_snapshot"])

    def test_students_cannot_drive_the_lifecycle(self) -> None:
        self.client.post(self.path + "/publish")
        self.sign_in("a0@example.edu")
        for route, body in (("/finalize", None), ("/reopen", {"reason": "x"}),
                            ("/unpublish", {"reason": "x"}), ("/recompute", None),
                            ("/events", None)):
            with self.subTest(route=route):
                call = self.client.get if route == "/events" else self.client.post
                response = call(self.path + route) if body is None else call(self.path + route, json=body)
                self.assertEqual(response.status_code, 403)


class FinalityTests(unittest.TestCase):
    def _assignment(self, **fields) -> models.Assignment:
        return models.Assignment(title="A", status=PUBLISHED, **fields)

    def test_a_section_without_a_deadline_is_never_settled(self) -> None:
        assignment = self._assignment(group_deadline=None, individual_deadline=None)
        self.assertFalse(is_final(assignment, True))
        self.assertFalse(is_final(assignment, False))

    def test_a_section_settles_when_its_own_deadline_passes(self) -> None:
        assignment = self._assignment(
            group_deadline=datetime.now(UTC) - timedelta(minutes=1),
            individual_deadline=datetime.now(UTC) + timedelta(days=1))
        self.assertTrue(is_final(assignment, True))
        self.assertFalse(is_final(assignment, False))

    def test_finalizing_settles_both_sections_and_a_draft_settles_neither(self) -> None:
        future = datetime.now(UTC) + timedelta(days=1)
        settled = self._assignment(group_deadline=future, individual_deadline=future)
        settled.status = FINALIZED
        self.assertTrue(is_final(settled, True))
        self.assertTrue(is_final(settled, False))

        draft = self._assignment(group_deadline=datetime.now(UTC) - timedelta(days=1))
        draft.status = DRAFT
        self.assertFalse(is_final(draft, True))


if __name__ == "__main__":
    unittest.main()
