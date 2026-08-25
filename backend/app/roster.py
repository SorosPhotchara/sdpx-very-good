"""Roster CSV import (PRD §7.2).

The import is atomic (FR-CLASS-02): one bad row rejects the whole file. A
half-imported roster is worse than no roster, because pairing then runs
silently on a class that is missing people.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from typing import Sequence

REQUIRED_HEADERS = ("email", "group_name")
OPTIONAL_HEADERS = ("student_id", "display_name")

#: Deliberately conservative. This gates a grade-bearing roster; it is not an
#: attempt to implement RFC 5322.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

#: Cells starting with these are executed as formulas by Excel and Sheets.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class RosterImportError(Exception):
    """Raised when the file cannot be read as a roster at all."""


@dataclass(frozen=True)
class RosterRow:
    line: int
    email_raw: str
    email_normalized: str
    group_name: str
    student_id: str | None = None
    display_name: str | None = None


@dataclass(frozen=True)
class RosterIssue:
    line: int | None
    kind: str
    message: str


@dataclass(frozen=True)
class RosterImportResult:
    rows: tuple[RosterRow, ...] = ()
    errors: tuple[RosterIssue, ...] = ()
    warnings: tuple[RosterIssue, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors


def normalize_email(raw: str) -> str:
    """Fold an address to the form used to match a login against the roster.

    Lowercase, drop a ``+tag`` suffix, then remove dots from the local part, so
    that ``Somchai.A+x@uni.ac.th`` and ``somchaia@uni.ac.th`` resolve to the
    same person (FR-AUTH-03).

    Raises:
        ValueError: if ``raw`` is not a plausible address.
    """
    candidate = raw.strip().lower()
    if not _EMAIL_RE.match(candidate):
        raise ValueError(f"malformed email address: {raw!r}")

    local, _, domain = candidate.partition("@")
    local = local.split("+", 1)[0].replace(".", "")
    if not local:
        raise ValueError(f"email has no local part once normalized: {raw!r}")
    return f"{local}@{domain}"


def escape_csv_cell(value: str) -> str:
    """Neutralise spreadsheet formula injection (FR-SEC-04).

    Applied on import *and* export: a roster row reading ``=cmd|'/c calc'!A1``
    is a payload aimed at whoever opens the exported grade sheet.
    """
    if value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def parse_roster_csv(text: str) -> RosterImportResult:
    """Parse and validate a roster CSV.

    Line numbers in issues are 1-based file lines counting the header, so they
    match what the instructor sees in their editor.

    Raises:
        RosterImportError: if the file is empty or the header is unusable.
    """
    reader = csv.reader(io.StringIO(text))
    try:
        raw_header = next(reader)
    except StopIteration:
        raise RosterImportError("ไฟล์ว่าง — ต้องมีอย่างน้อยบรรทัด header") from None

    header = [column.strip().lower() for column in raw_header]  # FR-CLASS-01
    missing = [column for column in REQUIRED_HEADERS if column not in header]
    if missing:
        raise RosterImportError("header ไม่ครบ — ขาดคอลัมน์: " + ", ".join(missing))

    index = {name: position for position, name in enumerate(header)}
    errors: list[RosterIssue] = []
    rows: list[RosterRow] = []
    seen: dict[str, int] = {}

    for line, record in enumerate(reader, start=2):
        if not any(cell.strip() for cell in record):
            continue  # a blank trailing line is not a data error

        def cell(name: str, record: list[str] = record) -> str:
            position = index.get(name)
            if position is None or position >= len(record):
                return ""
            return escape_csv_cell(record[position].strip())

        email_raw = cell("email")
        group_name = cell("group_name")

        if not group_name:
            errors.append(
                RosterIssue(line, "empty_group", f"แถว {line}: group_name ว่าง")
            )

        try:
            email_normalized = normalize_email(email_raw)
        except ValueError:
            errors.append(
                RosterIssue(
                    line,
                    "malformed_email",
                    f"แถว {line}: อีเมลผิดรูปแบบ ({email_raw!r})",
                )
            )
            continue

        first_seen = seen.get(email_normalized)
        if first_seen is not None:
            errors.append(
                RosterIssue(
                    line,
                    "duplicate_email",
                    f"แถว {line}: อีเมลซ้ำกับแถว {first_seen} ({email_normalized})",
                )
            )
            continue
        seen[email_normalized] = line

        rows.append(
            RosterRow(
                line=line,
                email_raw=email_raw,
                email_normalized=email_normalized,
                group_name=group_name,
                student_id=cell("student_id") or None,
                display_name=cell("display_name") or None,
            )
        )

    warnings = tuple(_undersized_group_warnings(rows))

    if errors:
        # FR-CLASS-02: reject the whole file, but keep every error so the
        # instructor fixes them in one pass instead of one upload per typo.
        return RosterImportResult(rows=(), errors=tuple(errors), warnings=warnings)
    return RosterImportResult(rows=tuple(rows), errors=(), warnings=warnings)


def _undersized_group_warnings(rows: Sequence[RosterRow]) -> list[RosterIssue]:
    """Groups smaller than 2 are reported, not rejected (FR-CLASS-03).

    They are legal — a student whose partner dropped the course still needs a
    row — but they cannot take part in individual evaluation (§8.3), so the
    instructor has to learn about it before publishing, not after.
    """
    sizes: dict[str, int] = {}
    for row in rows:
        sizes[row.group_name] = sizes.get(row.group_name, 0) + 1
    return [
        RosterIssue(
            None,
            "undersized_group",
            f"กลุ่ม {name!r} มีสมาชิก {size} คน (< 2) — "
            "จะไม่มีการประเมินรายบุคคลในกลุ่มนี้",
        )
        for name, size in sorted(sizes.items())
        if size < 2
    ]
