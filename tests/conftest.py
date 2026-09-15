from __future__ import annotations

import pytest

from factories import make_roster_csv, make_roster_row


@pytest.fixture
def valid_csv() -> str:
    return make_roster_csv(
        [
            make_roster_row(email="a@uni.ac.th", group_name="Aurora"),
            make_roster_row(email="b@uni.ac.th", group_name="Nova"),
            make_roster_row(email="c@uni.ac.th", group_name="Orion"),
        ]
    )


@pytest.fixture
def csv_with_bad_row_42() -> str:
    # Header is line 1, so data row N sits at file line N + 1. A 99-row
    # roster (lines 2-100) puts the file at exactly 100 lines total.
    rows = [
        make_roster_row(email=f"student{i}@uni.ac.th", group_name=f"Group{i}")
        for i in range(1, 100)
    ]
    rows[40] = make_roster_row(email="not-an-email", group_name="Group41")
    return make_roster_csv(rows)
