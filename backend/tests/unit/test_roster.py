"""Roster CSV import tests (PRD §7.2)."""

from __future__ import annotations

import pytest

from app.roster import (
    RosterImportError,
    escape_csv_cell,
    normalize_email,
    parse_roster_csv,
)

HEADER = "email,group_name,student_id,display_name"


def _csv(*rows: str) -> str:
    return "\n".join((HEADER, *rows)) + "\n"


# ---------------------------------------------------------------------------
# FR-AUTH-03 — email normalisation
# ---------------------------------------------------------------------------


def test_roster_address_and_login_address_resolve_to_the_same_person():
    """The example straight out of FR-AUTH-03."""
    assert normalize_email("Somchai.A+x@uni.ac.th") == normalize_email(
        "somchaia@uni.ac.th"
    )


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("  Nok@UNI.ac.th ", "nok@uni.ac.th"),
        ("n.o.k@uni.ac.th", "nok@uni.ac.th"),
        ("nok+fall2026@uni.ac.th", "nok@uni.ac.th"),
        ("nok+a.b@uni.ac.th", "nok@uni.ac.th"),
    ],
)
def test_case_dots_and_plus_tags_are_folded_away(raw, expected):
    assert normalize_email(raw) == expected


@pytest.mark.parametrize(
    "raw", ["", "no-at-sign", "two@@uni.ac.th", "nok@nodot", "a b@uni.ac.th"]
)
def test_implausible_addresses_are_rejected(raw):
    with pytest.raises(ValueError):
        normalize_email(raw)


def test_an_address_that_normalizes_to_nothing_is_rejected():
    with pytest.raises(ValueError):
        normalize_email("+tag@uni.ac.th")


# ---------------------------------------------------------------------------
# FR-CLASS-01/02/03 — import
# ---------------------------------------------------------------------------


def test_a_clean_roster_imports_every_row():
    result = parse_roster_csv(
        _csv(
            "nok@uni.ac.th,Aurora,6501,Nok",
            "ton@uni.ac.th,Aurora,6502,Ton",
            "mai@uni.ac.th,Borealis,6503,Mai",
            "fah@uni.ac.th,Borealis,6504,Fah",
        )
    )

    assert result.ok
    assert len(result.rows) == 4
    assert result.rows[0].group_name == "Aurora"


def test_header_matching_ignores_case_and_surrounding_space():
    """FR-CLASS-01."""
    text = " Email , Group_Name \nnok@uni.ac.th,Aurora\nton@uni.ac.th,Aurora\n"

    result = parse_roster_csv(text)

    assert result.ok
    assert len(result.rows) == 2


def test_one_bad_row_rejects_the_entire_file():
    """FR-CLASS-02 — a half-imported roster silently pairs a short class."""
    result = parse_roster_csv(
        _csv(
            "nok@uni.ac.th,Aurora,6501,Nok",
            "not-an-email,Aurora,6502,Ton",
            "mai@uni.ac.th,Borealis,6503,Mai",
        )
    )

    assert not result.ok
    assert result.rows == ()


def test_a_rejected_file_names_the_line_that_broke_it():
    rows = [f"student{n}@uni.ac.th,Aurora,{n}," for n in range(1, 100)]
    rows[40] = "broken-address,Aurora,41,"  # file line 42

    result = parse_roster_csv(_csv(*rows))

    assert not result.ok
    assert any(issue.line == 42 for issue in result.errors)


def test_every_error_is_reported_at_once_rather_than_one_upload_at_a_time():
    result = parse_roster_csv(
        _csv(
            "bad-one,Aurora,1,",
            "bad-two,Aurora,2,",
            "nok@uni.ac.th,,3,",
        )
    )

    kinds = {issue.kind for issue in result.errors}
    assert kinds == {"malformed_email", "empty_group"}
    assert len(result.errors) == 3


def test_duplicate_emails_are_caught_after_normalisation_not_before():
    """``n.o.k@`` and ``nok@`` are one student, and one student is one row."""
    result = parse_roster_csv(
        _csv("nok@uni.ac.th,Aurora,1,", "n.o.k@uni.ac.th,Borealis,2,")
    )

    assert not result.ok
    assert any(issue.kind == "duplicate_email" for issue in result.errors)


def test_an_empty_group_name_is_an_error_not_a_default():
    result = parse_roster_csv(_csv("nok@uni.ac.th,,1,"))

    assert not result.ok
    assert any(issue.kind == "empty_group" for issue in result.errors)


def test_a_group_with_one_member_warns_but_still_imports():
    """FR-CLASS-03 — legal, but it cannot take part in individual eval (§8.3)."""
    result = parse_roster_csv(
        _csv(
            "nok@uni.ac.th,Aurora,1,",
            "ton@uni.ac.th,Aurora,2,",
            "solo@uni.ac.th,Solo,3,",
        )
    )

    assert result.ok
    assert len(result.rows) == 3
    assert any(issue.kind == "undersized_group" for issue in result.warnings)


def test_blank_trailing_lines_are_not_treated_as_broken_rows():
    result = parse_roster_csv(
        HEADER + "\nnok@uni.ac.th,Aurora,1,\nton@uni.ac.th,Aurora,2,\n\n\n"
    )

    assert result.ok
    assert len(result.rows) == 2


def test_a_missing_required_header_stops_the_import_immediately():
    with pytest.raises(RosterImportError):
        parse_roster_csv("email,student_id\nnok@uni.ac.th,1\n")


def test_an_empty_file_stops_the_import_immediately():
    with pytest.raises(RosterImportError):
        parse_roster_csv("")


# ---------------------------------------------------------------------------
# FR-SEC-04 — spreadsheet formula injection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload", ["=cmd|'/c calc'!A1", "+1+1", "-1+1", "@SUM(A1:A9)"]
)
def test_cells_that_excel_would_execute_are_defused(payload):
    assert escape_csv_cell(payload).startswith("'")


def test_ordinary_cells_are_left_alone():
    assert escape_csv_cell("Aurora") == "Aurora"


def test_a_formula_in_a_group_name_survives_import_as_inert_text():
    result = parse_roster_csv(
        _csv("nok@uni.ac.th,=HYPERLINK(\"evil\"),1,", "ton@uni.ac.th,Aurora,2,")
    )

    assert result.ok
    assert result.rows[0].group_name.startswith("'=")
