"""Validate and import classroom membership from CSV."""

import csv
from dataclasses import dataclass
from io import StringIO

from email_validator import EmailNotValidError, validate_email
from sqlalchemy.orm import Session

from . import models


@dataclass(frozen=True)
class RosterRow:
    email: str
    group_name: str


@dataclass(frozen=True)
class ParsedRoster:
    rows: list[RosterRow]
    errors: list[str]


def parse_roster(csv_text: str) -> ParsedRoster:
    reader = csv.reader(StringIO(csv_text), strict=True)
    try:
        headers = next(reader)
    except (StopIteration, csv.Error):
        return ParsedRoster([], ["The CSV file is empty or malformed"])
    names = [header.strip().lstrip("\ufeff").lower().replace("_", "").replace(" ", "") for header in headers]
    if "email" not in names or "groupname" not in names:
        return ParsedRoster([], ["CSV needs email and groupname columns"])

    email_index = names.index("email")
    group_index = names.index("groupname")
    rows: list[RosterRow] = []
    errors: list[str] = []
    seen: set[str] = set()
    try:
        for cells in reader:
            if not cells or all(not cell.strip() for cell in cells):
                continue
            line = reader.line_num
            if len(cells) != len(headers):
                errors.append(f"Row {line}: wrong number of columns")
                continue
            try:
                email = validate_email(cells[email_index].strip(), check_deliverability=False).normalized.lower()
            except EmailNotValidError:
                errors.append(f"Row {line}: invalid email")
                continue
            group_name = cells[group_index].strip()
            if not group_name or group_name[0] in "=+-@":
                errors.append(f"Row {line}: invalid group name")
            if email in seen:
                errors.append(f"Row {line}: duplicate email")
            seen.add(email)
            rows.append(RosterRow(email, group_name))
    except csv.Error:
        errors.append("The CSV file is malformed")
    if not rows and not errors:
        errors.append("CSV has no students")
    return ParsedRoster([] if errors else rows, errors)


def import_roster(db: Session, classroom_id: int, csv_text: str) -> ParsedRoster:
    parsed = parse_roster(csv_text)
    if parsed.errors:
        return parsed
    if db.query(models.Student.id).filter_by(classroom_id=classroom_id).first():
        return ParsedRoster([], ["Classroom already has a roster"])

    groups = {
        group.name: group
        for group in db.query(models.Group).filter_by(classroom_id=classroom_id).all()
    }
    try:
        for row in parsed.rows:
            if row.group_name not in groups:
                group = models.Group(name=row.group_name, classroom_id=classroom_id)
                db.add(group)
                db.flush()
                groups[row.group_name] = group
            db.add(models.Student(
                email=row.email,
                group_name=row.group_name,
                group_id=groups[row.group_name].id,
                classroom_id=classroom_id,
            ))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return parsed
