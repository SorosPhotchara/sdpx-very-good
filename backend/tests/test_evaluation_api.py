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
        self.classroom_id = classroom_id
        # Four groups keep one eligible evaluator spare for the A-B pair once every
        # eligible student is guaranteed work, which the extra-pair tests rely on.
        sizes = {"A": 3, "B": 3, "C": 4, "D": 2}
        roster = "email,groupname\n" + "\n".join(
            f"{group}{index}@example.edu,{group}"
            for group, size in sizes.items() for index in range(size)
        )
        self.assertEqual(self.client.post(f"/classrooms/{classroom_id}/roster/import", json={"csv_text": roster}).json()["imported"], 12)
        self.assignment_id = self.client.post(f"/classrooms/{classroom_id}/assignments", json={
            "title": "Review", "group_score": 10,
            "group_deadline": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
            "group_criteria": [{"name": "Quality", "weight": 100}],
        }).json()["id"]
        self.client.post(f"/assignments/{self.assignment_id}/publish")
        with Session(self.engine) as db:
            pair = db.query(models.Pair).first()
            student = db.get(models.Student, pair.assigned_to_student_id)
            self.email = student.email
            self.student_id = student.id
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

    def _answer_one_group_pair(self, assignment_id: int, choice: int) -> None:
        """Submit a single group answer on one of the assignment's pairs."""
        with Session(self.engine) as db:
            pair = db.query(models.Pair).filter_by(assignment_id=assignment_id).first()
            email = db.get(models.Student, pair.assigned_to_student_id).email
            pair_id = pair.id
        self.sign_in(email)
        path = f"/assignments/{assignment_id}/evaluation/group"
        self.assertEqual(self.client.put(path + "/draft", json={
            "changes": [{"pair_id": pair_id, "choice": choice}]}).status_code, 200)
        self.assertEqual(self.client.post(path + "/submit").status_code, 200)

    def _scored_groups(self, assignment_id: int) -> list[float]:
        self.sign_in("teacher@example.edu", True)
        report = self.client.get(f"/assignments/{assignment_id}/report").json()
        return sorted(round(group["work_score"], 6) for group in report["groups"]
                      if group["work_score"] is not None)

    def test_group_work_scores_use_the_assignments_own_band(self) -> None:
        # One answer at the top of the scale, so the favoured group lands on the
        # band ceiling and the other on its floor: the band becomes observable
        # end to end rather than only inside the scoring unit tests.
        self._answer_one_group_pair(self.assignment_id, 1)
        self.assertEqual(self._scored_groups(self.assignment_id), [6.0, 10.0])

        # The same answer on an assignment with a wider band must score
        # differently, which only holds if the band is read per assignment.
        wide = self.client.post(f"/classrooms/{self.classroom_id}/assignments", json={
            "title": "Wide band", "group_score": 10,
            "score_floor": 0.0, "score_ceiling": 1.0,
            "group_deadline": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
            "group_criteria": [{"name": "Quality", "weight": 100}],
        }).json()["id"]
        self.assertEqual(self.client.post(f"/assignments/{wide}/publish").status_code, 200)
        self._answer_one_group_pair(wide, 1)
        self.assertEqual(self._scored_groups(wide), [0.0, 10.0])

    def test_feasibility_reports_the_achievable_plan_before_publishing(self) -> None:
        # FR-PAIR-04: groups of 3, 3, 4 and 2 make 6 pairs among 12 students, so
        # the coverage target of 5 is reachable at 3 pairs per student.
        self.sign_in("teacher@example.edu", True)
        plan = self.client.get(f"/assignments/{self.assignment_id}/feasibility")
        self.assertEqual(plan.status_code, 200)
        body = plan.json()
        self.assertEqual((body["students"], body["groups"], body["target_coverage"]), (12, 4, 5))
        self.assertEqual(body["group"]["pairs"], 6)
        self.assertEqual(body["group"]["coverage"], 5)
        self.assertEqual(body["group"]["workload"], 3)
        self.assertFalse(body["group"]["reduced"])
        self.assertEqual(body["group"]["reason"], "")
        self.assertEqual(body["group"]["criteria"], 1)
        self.assertEqual(body["group"]["total_comparisons"], 30)
        # The two-member group can hold no individual evaluation at all.
        two = next(item for item in body["individual"]["groups"] if item["members"] == 2)
        self.assertFalse(two["feasible"])
        self.assertIn("อย่างน้อย 3 คน", two["reason"])

        self.sign_in(self.email)
        self.assertEqual(
            self.client.get(f"/assignments/{self.assignment_id}/feasibility").status_code, 403)

    def test_feasibility_explains_a_reduced_coverage_target(self) -> None:
        # §8.2 example 2: three groups of four leave each pair only one eligible
        # evaluator's worth of workload, so the target has to come down.
        self.sign_in("teacher@example.edu", True)
        classroom_id = self.client.post("/classrooms/", json={"name": "Small"}).json()["id"]
        roster = "email,groupname\n" + "\n".join(
            f"s{group}{index}@small.edu,{group}"
            for group in ("A", "B", "C") for index in range(4))
        self.assertEqual(self.client.post(f"/classrooms/{classroom_id}/roster/import",
                                         json={"csv_text": roster}).json()["imported"], 12)
        small = self.client.post(f"/classrooms/{classroom_id}/assignments", json={
            "title": "Small room", "group_score": 10,
            "group_deadline": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
            "group_criteria": [{"name": "Quality", "weight": 100}],
        }).json()["id"]
        body = self.client.get(f"/assignments/{small}/feasibility").json()
        self.assertEqual(body["group"]["coverage"], 4)      # not the requested 5
        self.assertEqual(body["group"]["workload"], 1)
        self.assertTrue(body["group"]["reduced"])
        self.assertIn("4 ครั้งต่อคู่", body["group"]["reason"])

    def test_participation_multiplier_scales_only_the_personal_score(self) -> None:
        self._answer_one_group_pair(self.assignment_id, 1)
        self.sign_in("teacher@example.edu", True)
        report = self.client.get(f"/assignments/{self.assignment_id}/report").json()

        # Group evaluation never shows a student their own group, so the two
        # groups that got compared contain nobody who answered anything.
        scored = [item for item in report["groups"] if item["work_score"] is not None]
        self.assertEqual(len(scored), 2)
        member = next(row for row in report["students"]
                      if row["group_id"] == scored[0]["group_id"])
        self.assertEqual(member["submitted_comparisons"], 0)
        self.assertGreater(member["assigned_comparisons"], 0)
        self.assertEqual(member["participation_multiplier"], 0.0)
        self.assertEqual(member["final_score"], 0.0)
        # D5 / FR-SCORE-11: the group keeps its score regardless.
        self.assertAlmostEqual(member["group_work_score"], scored[0]["work_score"])
        self.assertIn(round(scored[0]["work_score"], 6), (6.0, 10.0))

        # The student who did answer is in a third group, which has no
        # comparisons yet, so their personal total is absent rather than zero.
        answered = next(row for row in report["students"]
                        if row["submitted_comparisons"] > 0)
        self.assertGreater(answered["participation_multiplier"], 0)
        self.assertIsNone(answered["group_work_score"])
        self.assertIsNone(answered["final_score"])

    def test_completion_threshold_is_configurable_and_validated(self) -> None:
        self.sign_in("teacher@example.edu", True)
        lenient = self.client.post(f"/classrooms/{self.classroom_id}/assignments", json={
            "title": "Lenient", "group_score": 10,
            "completion_threshold": 0.5,
            "group_deadline": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
            "group_criteria": [{"name": "Quality", "weight": 100}],
        }).json()["id"]
        self.assertEqual(
            self.client.get(f"/assignments/{lenient}/setup").json()["completion_threshold"], 0.5)
        for threshold in (0, -0.2, 1.5):
            response = self.client.post(f"/classrooms/{self.classroom_id}/assignments", json={
                "title": "Bad threshold", "group_score": 10,
                "completion_threshold": threshold,
                "group_deadline": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                "group_criteria": [{"name": "Quality", "weight": 100}],
            })
            self.assertEqual(response.status_code, 422, threshold)

    def test_setup_round_trip_keeps_a_configured_band(self) -> None:
        self.sign_in("teacher@example.edu", True)
        narrow = self.client.post(f"/classrooms/{self.classroom_id}/assignments", json={
            "title": "Narrow band", "group_score": 10,
            "score_floor": 0.25, "score_ceiling": 0.75,
            "group_deadline": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
            "group_criteria": [{"name": "Quality", "weight": 100}],
        }).json()["id"]
        setup = self.client.get(f"/assignments/{narrow}/setup").json()
        self.assertEqual((setup["score_floor"], setup["score_ceiling"]), (0.25, 0.75))

        # A setup PUT that omits the band must leave it alone rather than
        # silently restoring the defaults.
        del setup["score_floor"], setup["score_ceiling"]
        self.assertEqual(self.client.put(f"/assignments/{narrow}/setup", json=setup).status_code, 200)
        kept = self.client.get(f"/assignments/{narrow}/setup").json()
        self.assertEqual((kept["score_floor"], kept["score_ceiling"]), (0.25, 0.75))

    def test_invalid_band_is_rejected(self) -> None:
        self.sign_in("teacher@example.edu", True)
        for floor, ceiling in ((0.8, 0.8), (0.9, 0.4), (-0.1, 1.0), (0.5, 1.5)):
            response = self.client.post(f"/classrooms/{self.classroom_id}/assignments", json={
                "title": "Bad band", "group_score": 10,
                "score_floor": floor, "score_ceiling": ceiling,
                "group_deadline": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                "group_criteria": [{"name": "Quality", "weight": 100}],
            })
            self.assertEqual(response.status_code, 422, (floor, ceiling))

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
        self.assertEqual(self.client.put(self.path + "/draft", json={"changes": [{"pair_id": self.pair_id, "choice": 7}]}).status_code, 422)
        self.assertEqual(self.client.put(self.path + "/draft", json={"changes": [{"pair_id": self.pair_id, "choice": 6}]}).status_code, 200)
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
        self.assertGreater(after["submitted_comparisons"], 0)
        self.assertGreater(after["participation_multiplier"], 0)
        self.assertNotIn("students", after)
        self.sign_in("teacher@example.edu", True)
        report = self.client.get(f"/assignments/{self.assignment_id}/report").json()
        self.assertEqual(len(report["students"]), 12)
        self.assertTrue(any(group["work_score"] is not None for group in report["groups"]))
        with Session(self.engine) as db:
            pair = db.get(models.Pair, self.pair_id)
            pair_ids = {pair.left_group_id, pair.right_group_id}
        voted = next(row for row in report["coverage"] if {row["left_id"], row["right_id"]} == pair_ids)
        self.assertEqual(voted["votes"], 1)
        self.assertEqual(voted["missing_to_target"], voted["target_evaluations"] - 1)
        self.assertEqual(voted["shortage_to_target"], max(0, 5 - voted["target_evaluations"]))
        exported = self.client.get(f"/assignments/{self.assignment_id}/report/pairs.csv")
        self.assertEqual(exported.status_code, 200)
        self.assertIn("Evaluator 1", exported.text)
        self.assertNotIn(self.email, exported.text)

    def test_my_scores_carries_interim_and_final_state(self) -> None:
        self.sign_in(self.email)
        before = self.client.get(f"/assignments/{self.assignment_id}/my-scores").json()
        self.assertFalse(before["group_final"])
        # No individual deadline is configured for this assignment, so that section never finalises.
        self.assertFalse(before["individual_final"])
        with Session(self.engine) as db:
            assignment = db.get(models.Assignment, self.assignment_id)
            assignment.group_deadline = datetime.now(UTC) - timedelta(minutes=1)
            db.commit()
        after = self.client.get(f"/assignments/{self.assignment_id}/my-scores").json()
        self.assertTrue(after["group_final"])
        self.assertFalse(after["individual_final"])
        self.assertNotIn("students", after)

    def test_coverage_rows_name_their_subjects(self) -> None:
        self.sign_in("teacher@example.edu", True)
        report = self.client.get(f"/assignments/{self.assignment_id}/report").json()
        group_names = {group["name"] for group in report["groups"]}
        rows = [row for row in report["coverage"] if row["section"] == "group"]
        self.assertTrue(rows)
        for row in rows:
            self.assertIn(row["left"], group_names)
            self.assertIn(row["right"], group_names)

    def test_individual_summary_export_scales_work_by_participation(self) -> None:
        import csv
        from io import StringIO

        self.sign_in(self.email)
        self.client.put(self.path + "/draft", json={"changes": [{"pair_id": self.pair_id, "choice": 1}]})
        self.client.post(self.path + "/submit")
        self.sign_in("teacher@example.edu", True)
        content = self.client.get(f"/assignments/{self.assignment_id}/report/students.csv").text
        rows = {row["email"]: row for row in csv.DictReader(StringIO(content))}
        for column in ("assigned_comparisons", "submitted_comparisons",
                       "participation_multiplier", "final_score"):
            self.assertIn(column, rows[self.email])

        # Someone in a compared group has a work score, so their personal total
        # has to be that score scaled by their own multiplier (§9.4).
        scored = next(row for row in rows.values() if row["group_work_score"] != "")
        self.assertAlmostEqual(float(scored["final_score"]),
                               float(scored["group_work_score"])
                               * float(scored["participation_multiplier"]))

        # The one evaluator is in a third group, which has no comparisons yet, so
        # their total is blank rather than zero.
        self.assertEqual(rows[self.email]["group_work_score"], "")
        self.assertEqual(rows[self.email]["final_score"], "")

    def test_raw_pair_report_shows_latest_evaluator_answer_only_to_instructor(self) -> None:
        path = f"/assignments/{self.assignment_id}/report/raw-pairs"
        self.sign_in(self.email)
        self.assertEqual(self.client.get(path).status_code, 403)
        self.client.put(self.path + "/draft", json={"changes": [{"pair_id": self.pair_id, "choice": 1}]})
        self.client.post(self.path + "/submit")
        self.client.put(self.path + "/draft", json={"changes": [{"pair_id": self.pair_id, "choice": 5}]})
        self.client.post(self.path + "/submit")
        self.sign_in("other@example.edu", True)
        self.assertEqual(self.client.get(path).status_code, 403)
        self.sign_in("teacher@example.edu", True)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.json() if item["pair_id"] == self.pair_id)
        self.assertIsInstance(row["criterion_id"], int)
        self.assertEqual(row["evaluator_student_id"], self.student_id)
        self.assertEqual(row["evaluator"], self.email)
        self.assertEqual(row["choice"], 5)
        self.assertIsNotNone(row["submitted_at"])
        csv_response = self.client.get(f"/assignments/{self.assignment_id}/report/pairs.csv",
                                       headers={"Origin": "http://localhost:5173"})
        self.assertNotIn(self.email, csv_response.text)
        self.assertRegex(csv_response.headers["content-disposition"], r'Course_Review_raw_pairs_\d{8}\.csv')
        self.assertIn("Content-Disposition", csv_response.headers["access-control-expose-headers"])
        xlsx_response = self.client.get(f"/assignments/{self.assignment_id}/report.xlsx")
        self.assertRegex(xlsx_response.headers["content-disposition"], r'Course_Review_report_\d{8}\.xlsx')

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
        history = self.client.get("/classrooms/1/reassignments").json()
        self.assertEqual(len(history), 1)
        # The audit entry names the student, both groups and the instructor who moved them.
        self.assertEqual(history[0]["student_email"], "a0@example.edu")
        self.assertEqual(history[0]["old_group_name"], "A")
        self.assertEqual(history[0]["new_group_name"], "B")
        self.assertEqual(history[0]["instructor_email"], "teacher@example.edu")
        report = self.client.get(f"/assignments/{self.assignment_id}/report").json()
        self.assertTrue(all(item["votes"] == 0 for item in report["coverage"]))
        with Session(self.engine) as db:
            self.assertTrue(db.query(models.Pair).filter(models.Pair.superseded_at.is_not(None)).first())
            active = db.query(models.Pair).filter_by(assignment_id=self.assignment_id, superseded_at=None).all()
            self.assertEqual(len(active), 29)
            self.assertEqual(len({pair.assigned_to_student_id for pair in active}), 12)
        self.sign_in("a0@example.edu")
        self.assertTrue(self.client.get("/classrooms/1/notifications").json())
        self.assertEqual(self.client.put(path, json={"group_id": target_id}).status_code, 403)

    def test_instructor_assigns_extra_student_pairs_with_eligibility_checks(self) -> None:
        with Session(self.engine) as db:
            criterion_id = db.query(models.Criteria.id).filter_by(assignment_id=self.assignment_id).first()[0]
            groups = {group.name: group.id for group in db.query(models.Group).all()}
            students = {student.email: student.id for student in db.query(models.Student).all()}
            assigned = {
                pair.assigned_to_student_id
                for pair in db.query(models.Pair).filter_by(criteria_id=criterion_id, superseded_at=None)
                if {pair.left_group_id, pair.right_group_id} == {groups["A"], groups["B"]}
            }
            extra_student = next(student for student in db.query(models.Student).filter_by(classroom_id=self.classroom_id)
                                 if student.group_id not in (groups["A"], groups["B"]) and student.id not in assigned)
        payload = {"criteria_id": criterion_id, "left_id": groups["A"], "right_id": groups["B"],
                   "student_id": extra_student.id}
        path = f"/assignments/{self.assignment_id}/student-pairs"
        self.assertEqual(self.client.post(path, json={**payload, "student_id": next(iter(assigned)),
                                                       "left_id": groups["B"], "right_id": groups["A"]}).status_code, 409)
        added = self.client.post(path, json=payload)
        self.assertEqual(added.status_code, 200)
        self.assertEqual(self.client.post(path, json={**payload, "left_id": groups["B"],
                                                       "right_id": groups["A"]}).status_code, 409)
        self.assertEqual(self.client.post(path, json={**payload, "student_id": students["a0@example.edu"]}).status_code, 422)
        self.assertEqual(self.client.post(path, json={**payload, "student_id": 999999}).status_code, 422)
        report = self.client.get(f"/assignments/{self.assignment_id}/report").json()
        covered = next(row for row in report["coverage"] if {row["left_id"], row["right_id"]} ==
                       {groups["A"], groups["B"]})
        self.assertEqual((covered["eligible_evaluators"], covered["target_evaluations"],
                          covered["assigned_evaluators"], covered["votes"]), (6, 5, 6, 0))
        self.sign_in(extra_student.email)
        self.assertEqual(self.client.post(path, json=payload).status_code, 403)
        pair_id = added.json()["pair_id"]
        self.assertIn(pair_id, [pair["id"] for pair in self.client.get(self.path).json()["pairs"]])
        self.assertEqual(self.client.put(self.path + "/draft", json={"changes": [
            {"pair_id": pair_id, "choice": 3},
        ]}).status_code, 200)
        self.assertEqual(self.client.post(self.path + "/submit").status_code, 200)

        self.sign_in("teacher@example.edu", True)
        report = self.client.get(f"/assignments/{self.assignment_id}/report").json()
        covered = next(row for row in report["coverage"] if {row["left_id"], row["right_id"]} ==
                       {groups["A"], groups["B"]})
        self.assertEqual((covered["votes"], covered["missing_to_target"],
                          covered["shortage_to_target"]), (1, 4, 0))

    def test_instructor_assigns_extra_individual_pair_to_unused_peer(self) -> None:
        self.sign_in("teacher@example.edu", True)
        classroom_id = self.client.post("/classrooms/", json={"name": "Individual course"}).json()["id"]
        roster = "email,groupname\n" + "\n".join(
            [*(f"A{index}@individual.edu,A" for index in range(8)),
             "B0@individual.edu,B", "C0@individual.edu,C"]
        )
        self.assertEqual(self.client.post(f"/classrooms/{classroom_id}/roster/import",
                                          json={"csv_text": roster}).json()["imported"], 10)
        # Complete enumeration would hand every eligible peer a pair (D4), leaving
        # nobody for the instructor to add. A workload ceiling of 8 makes
        # FR-PAIR-14 reduce coverage to 2 of the 6 eligible peers instead.
        individual_id = self.client.post(f"/classrooms/{classroom_id}/assignments", json={
            "title": "Individual", "individual_score": 10,
            "individual_max_workload": 8,
            "individual_deadline": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
            "individual_criteria": [{"name": "Contribution", "weight": 100}],
        }).json()["id"]
        self.assertEqual(self.client.post(f"/assignments/{individual_id}/publish").status_code, 200)
        with Session(self.engine) as db:
            criterion_id = db.query(models.Criteria.id).filter_by(assignment_id=individual_id).first()[0]
            students = {student.email: student.id for student in db.query(models.Student).filter_by(classroom_id=classroom_id)}
            left_id, right_id = students["a0@individual.edu"], students["a1@individual.edu"]
            assigned = {
                pair.assigned_to_student_id
                for pair in db.query(models.Pair).filter_by(criteria_id=criterion_id, superseded_at=None)
                if {pair.left_id, pair.right_id} == {left_id, right_id}
            }
            spare = next(student_id for email, student_id in students.items()
                         if email.startswith("a") and student_id not in assigned and student_id not in (left_id, right_id))
        individual_path = f"/assignments/{individual_id}/student-pairs"
        individual = {"criteria_id": criterion_id, "left_id": left_id,
                      "right_id": right_id, "student_id": spare}
        self.assertEqual(len(assigned), 2)
        self.assertEqual(self.client.post(individual_path, json={**individual, "student_id": next(iter(assigned)),
                                                                  "left_id": right_id, "right_id": left_id}).status_code, 409)
        self.assertEqual(self.client.post(individual_path, json=individual).status_code, 200)
        self.assertEqual(self.client.post(individual_path, json=individual).status_code, 409)
        self.assertEqual(self.client.post(individual_path, json={**individual, "student_id": left_id}).status_code, 422)
        self.assertEqual(self.client.post(individual_path, json={**individual,
                                                                 "student_id": students["b0@individual.edu"]}).status_code, 422)
        self.assertEqual(self.client.post(individual_path, json={**individual,
                                                                 "right_id": students["b0@individual.edu"]}).status_code, 422)

    def test_reassignment_preview_warns_about_submitted_answers_without_mutating(self) -> None:
        with Session(self.engine) as db:
            student = db.query(models.Student).filter_by(email="a0@example.edu").first()
            target = db.query(models.Group).filter_by(name="B").first()
            group_a = db.query(models.Group).filter_by(name="A").first()
            criterion = db.query(models.Criteria).filter_by(assignment_id=self.assignment_id).first()
            assigned = db.query(models.Pair).filter_by(assigned_to_student_id=student.id).first()
            busy = {
                pair.assigned_to_student_id
                for pair in db.query(models.Pair).filter_by(criteria_id=criterion.id, superseded_at=None)
                if {pair.left_group_id, pair.right_group_id} == {group_a.id, target.id}
            }
            evaluator = next(candidate for candidate in db.query(models.Student).filter_by(classroom_id=self.classroom_id)
                             if candidate.group_id not in (group_a.id, target.id) and candidate.id not in busy)
            student_id, old_group_id, target_id = student.id, group_a.id, target.id
            extra_payload = {"criteria_id": criterion.id, "left_id": group_a.id,
                             "right_id": target.id, "student_id": evaluator.id}
            affected_pair_id = assigned.id
        self.sign_in("a0@example.edu")
        self.assertEqual(self.client.put(self.path + "/draft", json={"changes": [
            {"pair_id": affected_pair_id, "choice": 3},
        ]}).status_code, 200)
        self.assertEqual(self.client.post(self.path + "/submit").status_code, 200)
        self.sign_in("teacher@example.edu", True)
        extra = self.client.post(f"/assignments/{self.assignment_id}/student-pairs", json=extra_payload)
        self.assertEqual(extra.status_code, 200)
        extra_id = extra.json()["pair_id"]
        path = f"/classrooms/{self.classroom_id}/students/{student_id}/group"
        preview = self.client.get(path + "/preview", params={"group_id": target_id})
        self.assertEqual(preview.status_code, 200)
        self.assertGreater(preview.json()["changed_pairs"], 0)
        self.assertGreater(preview.json()["affected_submissions"], 0)
        with Session(self.engine) as db:
            self.assertEqual(db.get(models.Student, student_id).group_id, old_group_id)
            self.assertIsNone(db.get(models.Pair, affected_pair_id).superseded_at)
            self.assertEqual(db.query(models.Reassignment).count(), 0)
        moved = self.client.put(path, json={"group_id": target_id})
        self.assertEqual(moved.status_code, 200)
        for key in ("changed_pairs", "new_pairs", "superseded_pairs", "affected_submissions"):
            self.assertEqual(moved.json()[key], preview.json()[key])
        with Session(self.engine) as db:
            self.assertIsNotNone(db.get(models.Pair, affected_pair_id).superseded_at)
            self.assertIsNone(db.get(models.Pair, extra_id).superseded_at)

    def test_every_student_can_open_the_group_section(self) -> None:
        self.sign_in("teacher@example.edu", True)
        roster = self.client.get("/students/", params={"classroom_id": self.classroom_id, "limit": 500})
        emails = [student["email"] for student in roster.json()]

        self.assertEqual(len(emails), 12)
        for email in emails:
            self.sign_in(email)
            page = self.client.get(self.path)
            self.assertEqual(page.status_code, 200, email)
            self.assertTrue(page.json()["is_open"], email)
            self.assertTrue(page.json()["pairs"], email)

    def test_reassignment_gives_work_back_to_a_student_left_without_pairs(self) -> None:
        with Session(self.engine) as db:
            mover = db.query(models.Student).filter_by(email="a0@example.edu").first()
            target = db.query(models.Group).filter_by(name="B").first()
            starved = db.query(models.Student).filter(
                models.Student.classroom_id == self.classroom_id,
                models.Student.id != mover.id,
            ).order_by(models.Student.id).first()
            # Drift this member into an empty section the way an earlier move would:
            # every assignment of theirs is superseded and nothing replaced it.
            for pair in db.query(models.Pair).filter_by(
                assigned_to_student_id=starved.id, superseded_at=None,
            ):
                pair.superseded_at = datetime.now(UTC)
            db.commit()
            mover_id, target_id, starved_id = mover.id, target.id, starved.id
            self.assertEqual(db.query(models.Pair).filter_by(
                assigned_to_student_id=starved_id, superseded_at=None,
            ).count(), 0)

        self.sign_in("teacher@example.edu", True)
        path = f"/classrooms/{self.classroom_id}/students/{mover_id}/group"
        preview = self.client.get(path + "/preview", params={"group_id": target_id})
        self.assertEqual(preview.status_code, 200)
        moved = self.client.put(path, json={"group_id": target_id})
        self.assertEqual(moved.status_code, 200)
        for key in ("changed_pairs", "new_pairs", "superseded_pairs", "affected_submissions"):
            self.assertEqual(moved.json()[key], preview.json()[key], key)

        with Session(self.engine) as db:
            self.assertGreaterEqual(db.query(models.Pair).filter_by(
                assigned_to_student_id=starved_id, superseded_at=None,
            ).count(), 1)
            self.assertTrue(db.query(models.Notification).filter_by(student_id=starved_id).first())
