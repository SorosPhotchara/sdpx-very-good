import csv
import unittest
from datetime import UTC, datetime, timedelta
from io import StringIO
from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models
from app.export import export_csv
from app.reports import raw_pair_responses
from app.routes.reports import _export_disposition
from app.xlsx_export import export_xlsx
from tests.support import TestDatabase


class ExportTests(unittest.TestCase):
    def test_raw_report_reveals_latest_evaluator_but_csv_keeps_pseudonym(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        models.Base.metadata.create_all(engine)
        try:
            with Session(engine) as db:
                classroom = models.Classroom(name="Course")
                db.add(classroom)
                db.flush()
                groups = [models.Group(name=name, classroom_id=classroom.id) for name in ("A", "B", "C")]
                db.add_all(groups)
                db.flush()
                student = models.Student(email="evaluator@example.edu", classroom_id=classroom.id, group_id=groups[2].id)
                assignment = models.Assignment(title="Review", classroom_id=classroom.id)
                db.add_all([student, assignment])
                db.flush()
                criterion = models.Criteria(assignment_id=assignment.id, name="Quality", is_group=True, weight=100)
                db.add(criterion)
                db.flush()
                pair = models.Pair(assignment_id=assignment.id, criteria_id=criterion.id, pair_type="group",
                                   left_group_id=groups[0].id, right_group_id=groups[1].id,
                                   assigned_to_student_id=student.id)
                db.add(pair)
                db.flush()
                for choice, seconds in ((1, 0), (5, 1)):
                    db.add(models.Submission(student_id=student.id, assignment_id=assignment.id, section="group",
                                             submitted_at=datetime.now(UTC) + timedelta(seconds=seconds),
                                             choices=[models.SubmissionChoice(pair_id=pair.id, choice=choice)]))
                db.commit()
                row = raw_pair_responses(db, assignment)[0]
                self.assertEqual((row["evaluator"], row["choice"]), (student.email, 5))
                exported = export_csv(db, assignment, "pairs")
                self.assertIn("Evaluator 1", exported)
                self.assertNotIn(student.email, exported)
        finally:
            engine.dispose()

    def test_export_filename_preserves_thai_names_without_header_unsafe_characters(self) -> None:
        from urllib.parse import unquote

        classroom = models.Classroom(id=7, name="ห้อง / วิชา")
        assignment = models.Assignment(id=9, title="งาน: ประเมิน", classroom_id=7, classroom=classroom)
        disposition = _export_disposition(assignment, "group_summary", "csv")
        encoded = disposition.split("filename*=UTF-8''", 1)[1]
        filename = unquote(encoded)
        self.assertRegex(filename, r"^ห้อง_วิชา_งาน_ประเมิน_group_summary_\d{8}\.csv$")
        self.assertNotIn("/", filename)
        self.assertNotIn("\n", disposition)

    def test_spreadsheet_formula_in_group_name_is_escaped(self) -> None:
        database = TestDatabase()
        try:
            with Session(database.engine) as db:
                classroom = models.Classroom(name="Course")
                db.add(classroom)
                db.flush()
                group = models.Group(name="=HYPERLINK(\"bad\")", classroom_id=classroom.id)
                assignment = models.Assignment(title="Review", classroom_id=classroom.id)
                db.add_all([group, assignment])
                db.commit()
                content = export_csv(db, assignment, "groups")
                row = list(csv.DictReader(StringIO(content)))[0]
                self.assertTrue(row["name"].startswith("'="))
                with ZipFile(BytesIO(export_xlsx(db, assignment))) as archive:
                    self.assertEqual(len([name for name in archive.namelist() if name.startswith("xl/worksheets/sheet")]), 3)
                    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
                    self.assertIn("Group Summary", ET.tostring(workbook, encoding="unicode"))
                    sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
                    self.assertIn("'=HYPERLINK", ET.tostring(sheet, encoding="unicode"))
        finally:
            database.close()
