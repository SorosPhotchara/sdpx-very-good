"""Generate a small three-sheet XLSX without runtime dependencies."""

from io import BytesIO
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.orm import Session

from . import models
from .export import _safe, sheet_data

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT = "http://schemas.openxmlformats.org/package/2006/content-types"
ET.register_namespace("", MAIN)


def _xml(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _column(number: int) -> str:
    name = ""
    while number:
        number, digit = divmod(number - 1, 26)
        name = chr(65 + digit) + name
    return name


def _clean(value: object) -> str:
    return "".join(char for char in str(value) if ord(char) >= 32 or char in "\t\n\r")


def _sheet(fields: tuple[str, ...], rows: list[dict]) -> bytes:
    root = ET.Element(f"{{{MAIN}}}worksheet")
    data = ET.SubElement(root, f"{{{MAIN}}}sheetData")
    for row_index, values in enumerate((fields, *([tuple(row[field] for field in fields) for row in rows])), 1):
        row_element = ET.SubElement(data, f"{{{MAIN}}}row", {"r": str(row_index)})
        for column_index, value in enumerate(values, 1):
            if value is None:
                continue
            cell = ET.SubElement(row_element, f"{{{MAIN}}}c", {"r": f"{_column(column_index)}{row_index}"})
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                ET.SubElement(cell, f"{{{MAIN}}}v").text = str(value)
            else:
                cell.set("t", "inlineStr")
                inline = ET.SubElement(cell, f"{{{MAIN}}}is")
                ET.SubElement(inline, f"{{{MAIN}}}t").text = _clean(_safe(value))
    return _xml(root)


def export_xlsx(db: Session, assignment: models.Assignment) -> bytes:
    sheets = (("Group Summary", "groups"), ("Individual Summary", "students"), ("Raw Pairs", "pairs"))
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        content = ET.Element(f"{{{CONTENT}}}Types")
        ET.SubElement(content, f"{{{CONTENT}}}Default", {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
        ET.SubElement(content, f"{{{CONTENT}}}Default", {"Extension": "xml", "ContentType": "application/xml"})
        ET.SubElement(content, f"{{{CONTENT}}}Override", {"PartName": "/xl/workbook.xml", "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"})
        for index in range(1, 4):
            ET.SubElement(content, f"{{{CONTENT}}}Override", {"PartName": f"/xl/worksheets/sheet{index}.xml", "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"})
        archive.writestr("[Content_Types].xml", _xml(content))

        relationships = ET.Element(f"{{{PKG}}}Relationships")
        ET.SubElement(relationships, f"{{{PKG}}}Relationship", {"Id": "rId1", "Type": REL + "/officeDocument", "Target": "xl/workbook.xml"})
        archive.writestr("_rels/.rels", _xml(relationships))

        workbook = ET.Element(f"{{{MAIN}}}workbook")
        sheet_list = ET.SubElement(workbook, f"{{{MAIN}}}sheets")
        workbook_rels = ET.Element(f"{{{PKG}}}Relationships")
        for index, (title, key) in enumerate(sheets, 1):
            ET.SubElement(sheet_list, f"{{{MAIN}}}sheet", {"name": title, "sheetId": str(index), f"{{{REL}}}id": f"rId{index}"})
            ET.SubElement(workbook_rels, f"{{{PKG}}}Relationship", {"Id": f"rId{index}", "Type": REL + "/worksheet", "Target": f"worksheets/sheet{index}.xml"})
            fields, rows = sheet_data(db, assignment, key)
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _sheet(fields, rows))
        archive.writestr("xl/workbook.xml", _xml(workbook))
        archive.writestr("xl/_rels/workbook.xml.rels", _xml(workbook_rels))
    return output.getvalue()
