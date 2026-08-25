"""AssignmentService tests — engines wired to storage through fakes."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain import Flag, Side
from app.repositories import ComparisonRepository, RosterRepository
from app.scoring import Participation, ScoringError
from app.services import AssignmentService
from tests.factories import (
    make_classroom,
    make_comparison,
    make_config,
    make_criterion,
    make_pair,
    make_student,
)
from tests.fakes.fake_comparison_repo import FakeComparisonRepo
from tests.fakes.fake_roster_repo import FakeRosterRepo


def test_the_fakes_satisfy_the_same_protocols_as_the_real_adapters():
    """A fake that has drifted gives green tests and a broken deploy."""
    assert isinstance(FakeRosterRepo(), RosterRepository)
    assert isinstance(FakeComparisonRepo(), ComparisonRepository)


def test_publishing_reports_the_coverage_that_will_actually_be_used(
    roster_repo, group_criteria
):
    # FR-PAIR-04: the instructor sees the numbers before pairs go live.
    service = AssignmentService(roster_repo)

    result = service.publish("classroom-1", "a1", group_criteria, make_config())

    assert result.feasibility.coverage == 4  # lowered from 5, §8.2 example 2
    assert result.warnings  # and the reduction is surfaced, not swallowed


def test_publishing_generates_pairs_for_every_group_criterion(
    roster_repo, group_criteria
):
    service = AssignmentService(roster_repo)

    result = service.publish("classroom-1", "a1", group_criteria, make_config())
    criteria_covered = {pair.criterion_id for pair in result.pairs}

    assert criteria_covered == {"ux", "completeness", "innovation"}


def test_individual_pairs_are_skipped_when_that_side_is_switched_off(
    roster_repo, group_criteria, individual_criteria
):
    """FR-ASSIGN-07 — individual_max_score = 0 means no individual pairs."""
    service = AssignmentService(roster_repo)

    result = service.publish(
        "classroom-1",
        "a1",
        [*group_criteria, *individual_criteria],
        make_config(individual_max_score=Decimal("0")),
    )

    assert all(pair.side is Side.GROUP for pair in result.pairs)


def test_a_two_person_group_is_reported_as_having_no_individual_evaluation(
    group_criteria, individual_criteria
):
    """FR-PAIR-12 + FR-EVAL-12 — students must be told why, not just shown nothing."""
    repo = FakeRosterRepo(
        [
            *make_classroom(num_groups=2, group_size=4),
            make_student(id="s90", email="s90@uni.ac.th", group_id="tiny"),
            make_student(id="s91", email="s91@uni.ac.th", group_id="tiny"),
        ]
    )
    service = AssignmentService(repo)

    result = service.publish(
        "classroom-1", "a1", [*group_criteria, *individual_criteria], make_config()
    )

    assert result.individual_plans["tiny"].enabled is False
    assert any("tiny" in warning for warning in result.warnings)


def test_publishing_a_classroom_with_no_students_is_refused(group_criteria):
    service = AssignmentService(FakeRosterRepo())

    with pytest.raises(Exception):
        service.publish("classroom-1", "a1", group_criteria, make_config())


def test_criteria_that_do_not_total_one_hundred_percent_block_publish(roster_repo):
    """FR-ASSIGN-02 — validated before pairs exist, not after."""
    service = AssignmentService(roster_repo)
    broken = [make_criterion(id="ux", weight_pct=Decimal("30"))]

    with pytest.raises(ScoringError):
        service.publish("classroom-1", "a1", broken, make_config())


def test_final_score_multiplies_both_components_by_the_participation_ratio(
    roster_repo, group_criteria
):
    student = make_student(id="s1", group_id="g1")
    comparisons = [
        make_comparison(
            pair=make_pair(
                criterion_id=criterion.id,
                item_a_id="g1",
                item_b_id="g2",
                display_left_item_id="g1",
            ),
            choice=1,
        )
        for criterion in group_criteria
        for _ in range(3)
    ]
    comparison_repo = FakeComparisonRepo(
        comparisons,
        {
            "s1": Participation(
                submitted_group=6,
                assigned_group=12,
                submitted_individual=0,
                assigned_individual=0,
            )
        },
    )
    service = AssignmentService(roster_repo, comparison_repo)

    result = service.final_score("a1", student, group_criteria, make_config())

    # q = 1.0 everywhere → ratio 1.000 → group component is the full 15.
    assert result.group_component == Decimal("15.00")
    assert result.participation_ratio == Decimal("0.5")
    assert result.total < result.group_component


def test_scoring_without_a_comparison_repository_fails_loudly(
    roster_repo, group_criteria
):
    service = AssignmentService(roster_repo)

    with pytest.raises(ScoringError):
        service.score_item("a1", "g1", Side.GROUP, group_criteria, make_config())


def test_an_item_nobody_compared_is_flagged_rather_than_scored_zero(
    roster_repo, group_criteria
):
    service = AssignmentService(roster_repo, FakeComparisonRepo())

    component = service.score_item(
        "a1", "g-unseen", Side.GROUP, group_criteria, make_config()
    )

    assert component.total == Decimal("0")
    assert Flag.LOW_CONFIDENCE in component.flags
