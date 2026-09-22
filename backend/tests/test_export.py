import csv
import unittest
from io import StringIO
from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from sqlalchemy.orm import Session

from app import models
from app.export import export_csv
from app.xlsx_export import export_xlsx
from tests.support import TestDatabase


class ExportTests(unittest.TestCase):
    def test_spreadsheet_formula_in_group_name_is_escaped(self) -> None:
        database = TestDatabase()
        try:
            with Session(database.engine) as db:
                classroom = models.Classroom(name="Course", instructor_emails="teacher@example.edu")
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
