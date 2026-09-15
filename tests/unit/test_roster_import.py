from __future__ import annotations

from app.domain.roster import normalize_email, parse_roster


def test_roster_address_and_login_address_resolve_to_the_same_person() -> None:
    roster_address = "Student+cohort2026@Uni.ac.th"
    login_address = " student@uni.ac.th "

    assert normalize_email(roster_address) == normalize_email(login_address)


def test_case_and_plus_tags_are_folded_away() -> None:
    assert normalize_email(" Student+team@Uni.ac.th ") == "student@uni.ac.th"


def test_implausible_addresses_are_rejected() -> None:
    result = parse_roster("email,group_name\nnot-an-email,Aurora")

    assert result.rows == []
    assert result.errors == ["Row 2: invalid email"]


def test_header_matching_ignores_case_and_surrounding_space() -> None:
    result = parse_roster(" Email , Group Name \nstudent@uni.ac.th,Aurora")

    assert result.errors == []
    assert result.rows[0].group_name == "Aurora"


def test_one_bad_row_rejects_the_entire_file() -> None:
    result = parse_roster(
        "email,group_name\nstudent@uni.ac.th,Aurora\nnot-an-email,Nova"
    )

    assert result.rows == []
    assert result.errors == ["Row 3: invalid email"]


def test_a_rejected_file_names_the_row_that_broke_it(csv_with_bad_row_42: str) -> None:
    result = parse_roster(csv_with_bad_row_42)

    assert result.errors == ["Row 42: invalid email"]


def test_every_error_is_reported_at_once_rather_than_one_upload_at_a_time() -> None:
    result = parse_roster("email,group_name\nnot-an-email,\nstudent@uni.ac.th,Aurora")

    assert result.errors == [
        "Row 2: invalid email",
        "Row 2: group_name is required",
    ]


def test_duplicate_emails_are_caught_after_normalisation_not_before() -> None:
    result = parse_roster(
        "email,group_name\nstudent+one@uni.ac.th,Aurora\nSTUDENT@UNI.AC.TH,Nova"
    )

    assert result.errors == ["Row 3: duplicate email"]


def test_an_empty_group_name_is_an_error_not_a_default() -> None:
    result = parse_roster("email,group_name\nstudent@uni.ac.th,")

    assert result.errors == ["Row 2: group_name is required"]


def test_blank_lines_are_skipped_without_shifting_row_numbers() -> None:
    result = parse_roster(
        "email,group_name\nstudent@uni.ac.th,Aurora\n\nnot-an-email,Nova"
    )

    assert result.errors == ["Row 4: invalid email"]


def test_a_missing_required_header_stops_the_import_immediately() -> None:
    result = parse_roster("email,team\nstudent@uni.ac.th,Aurora")

    assert result.rows == []
    assert result.errors == ["Missing required header: group_name"]


def test_cells_that_excel_would_execute_are_defused() -> None:
    result = parse_roster(
        "email,group_name\nstudent@uni.ac.th,=cmd|' /C calc'!A0"
    )

    assert result.errors == []
    assert not result.rows[0].group_name.startswith(("=", "+", "-", "@"))


def test_a_formula_in_a_group_name_survives_import_as_inert_text() -> None:
    result = parse_roster("email,group_name\nstudent@uni.ac.th,=SUM(A1:A9)")

    assert result.errors == []
    assert result.rows[0].group_name == "'=SUM(A1:A9)"


def test_valid_csv_fixture_imports_with_no_errors(valid_csv: str) -> None:
    result = parse_roster(valid_csv)

    assert result.errors == []
    assert len(result.rows) == 3
