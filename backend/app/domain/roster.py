"""Roster import and pairing rules for Pairwise.

This is a Python port of the domain rules first prototyped in
src/domain/roster.ts, extended with the rules from TEST_PLAN.md that the
TypeScript version does not yet cover (CSV-formula defusal).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

REQUIRED_HEADERS = ("email", "group_name")

# Leading characters that a spreadsheet application (Excel, Sheets, LibreOffice)
# will interpret as the start of a formula if the cell is opened again later.
FORMULA_TRIGGER_CHARS = ("=", "+", "-", "@", "\t", "\r")

_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@dataclass(frozen=True)
class RosterRow:
    email: str
    group_name: str


@dataclass(frozen=True)
class RosterImportResult:
    rows: list[RosterRow] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PairAssignment:
    evaluator_email: str
    left_group: str
    right_group: str


def normalize_header(value: str) -> str:
    return "_".join(value.strip().lower().split())


def normalize_email(value: str) -> str:
    local_part, _, domain = value.strip().lower().partition("@")
    return f"{local_part.split('+')[0]}@{domain}"


def _is_plausible_email(value: str) -> bool:
    return bool(_EMAIL_PATTERN.match(value))


def _defuse_formula(value: str) -> str:
    # Prefix with a single quote, the same escape spreadsheets use to force a
    # cell to render as literal text instead of evaluating it as a formula.
    if value and value[0] in FORMULA_TRIGGER_CHARS:
        return f"'{value}"
    return value


def parse_roster(csv_text: str) -> RosterImportResult:
    lines = re.split(r"\r?\n", csv_text)
    header_index = next((i for i, line in enumerate(lines) if line.strip()), None)
    if header_index is None:
        return RosterImportResult(rows=[], errors=["The file is empty"])

    headers = [normalize_header(cell) for cell in lines[header_index].split(",")]
    missing_headers = [header for header in REQUIRED_HEADERS if header not in headers]
    if missing_headers:
        return RosterImportResult(
            rows=[],
            errors=[f"Missing required header: {', '.join(missing_headers)}"],
        )

    email_index = headers.index("email")
    group_index = headers.index("group_name")
    errors: list[str] = []
    rows: list[RosterRow] = []
    seen_emails: set[str] = set()

    for index, line in enumerate(lines):
        if index == header_index or line.strip() == "":
            continue

        cells = [cell.strip() for cell in line.split(",")]
        row_number = index + 1
        raw_email = cells[email_index] if email_index < len(cells) else ""
        raw_group = cells[group_index] if group_index < len(cells) else ""
        email = normalize_email(raw_email)
        group_name = _defuse_formula(raw_group)

        if not _is_plausible_email(email):
            errors.append(f"Row {row_number}: invalid email")
        if group_name == "":
            errors.append(f"Row {row_number}: group_name is required")
        if email in seen_emails:
            errors.append(f"Row {row_number}: duplicate email")
        if email != "" and _is_plausible_email(email):
            seen_emails.add(email)

        rows.append(RosterRow(email=email, group_name=group_name))

    if errors:
        return RosterImportResult(rows=[], errors=errors)
    return RosterImportResult(rows=rows, errors=[])


def allocate_pairs(rows: list[RosterRow]) -> list[PairAssignment]:
    """Assign every unique pair of groups to an evaluator outside that pair."""
    groups = list(dict.fromkeys(row.group_name for row in rows))
    assignments: list[PairAssignment] = []

    for evaluator in groups:
        evaluator_email = next(
            (row.email for row in rows if row.group_name == evaluator), None
        )
        if evaluator_email is None:
            continue
        for left_index in range(len(groups) - 1):
            for right_index in range(left_index + 1, len(groups)):
                left_group = groups[left_index]
                right_group = groups[right_index]
                if evaluator in (left_group, right_group):
                    continue
                assignments.append(
                    PairAssignment(
                        evaluator_email=evaluator_email,
                        left_group=left_group,
                        right_group=right_group,
                    )
                )

    return assignments
