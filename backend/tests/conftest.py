"""Shared fixtures for the PairEval engine tests.

The two classroom fixtures are the worked examples from PRD §8.2 — one that is
comfortably feasible and one that is not — because those are the two cases the
pairing engine has to get right.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain import Side
from tests.factories import make_config, make_criterion, make_classroom
from tests.fakes.fake_comparison_repo import FakeComparisonRepo
from tests.fakes.fake_roster_repo import FakeRosterRepo


@pytest.fixture
def config():
    return make_config()


@pytest.fixture
def group_criteria():
    """PRD §9.5: UX 40%, Completeness 35%, Innovation 25%."""
    return [
        make_criterion(id="ux", name="User Experience", weight_pct=Decimal("40")),
        make_criterion(id="completeness", name="Completeness", weight_pct=Decimal("35")),
        make_criterion(id="innovation", name="Innovation", weight_pct=Decimal("25")),
    ]


@pytest.fixture
def individual_criteria():
    """PRD §9.5: Teamwork 50%, Management 50%."""
    return [
        make_criterion(
            id="teamwork",
            side=Side.INDIVIDUAL,
            name="Teamwork",
            weight_pct=Decimal("50"),
        ),
        make_criterion(
            id="management",
            side=Side.INDIVIDUAL,
            name="Management",
            weight_pct=Decimal("50"),
        ),
    ]


@pytest.fixture
def large_classroom():
    """PRD §8.2 example 1 — S=200, N=10, 20 per group. Feasible at R=5."""
    return make_classroom(num_groups=10, group_size=20)


@pytest.fixture
def small_classroom():
    """PRD §8.2 example 2 — S=12, N=3, 4 per group. R must drop to 4."""
    return make_classroom(num_groups=3, group_size=4)


@pytest.fixture
def roster_repo(small_classroom):
    return FakeRosterRepo(small_classroom)


@pytest.fixture
def comparison_repo():
    return FakeComparisonRepo()
