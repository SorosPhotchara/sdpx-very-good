"""Pairing engine tests (PRD §8)."""

from __future__ import annotations

import pytest

from app.domain import PairingInfeasibleError, Side
from app.pairing import (
    check_invariants,
    coverage_by_pair,
    generate_group_pairs,
    generate_individual_pairs,
    individual_plan,
    solve_group_feasibility,
    workload_by_evaluator,
)
from tests.factories import make_classroom, make_config, make_criterion


def _sizes(students):
    sizes: dict[str, int] = {}
    for student in students:
        sizes[student.group_id] = sizes.get(student.group_id, 0) + 1
    return sizes


# ---------------------------------------------------------------------------
# §8.2 — feasibility
# ---------------------------------------------------------------------------


def test_large_room_reaches_the_default_coverage_of_five(large_classroom):
    """PRD §8.2 example 1: S=200, N=10 → R=5, k=2."""
    result = solve_group_feasibility(_sizes(large_classroom), make_config())

    assert result.coverage == 5
    assert result.workload == 2
    assert result.possible_pairs == 45
    assert result.total_comparisons == 225
    assert result.reduced is False


def test_small_room_lowers_coverage_to_four_because_five_is_impossible(small_classroom):
    """PRD §8.2 example 2: S=12, N=3 → R drops to 4, k=1."""
    result = solve_group_feasibility(_sizes(small_classroom), make_config())

    assert result.coverage == 4
    assert result.workload == 1
    assert result.reduced is True


def test_a_lowered_coverage_is_explained_in_numbers_not_just_warned_about(
    small_classroom,
):
    # FR-PAIR-05. A warning with no figures is one everybody learns to ignore.
    result = solve_group_feasibility(_sizes(small_classroom), make_config())

    assert "4" in result.reason and "5" in result.reason
    assert result.reason.strip() != ""


def test_coverage_is_capped_by_how_many_people_may_judge_the_hardest_pair():
    """Constraint (3): ``R ≤ min over pairs of (S − |a| − |b|)``.

    Two large groups and three tiny ones. The pair of large groups leaves only
    3 eligible judges in the whole classroom, so coverage 5 is impossible even
    though nobody is anywhere near their workload ceiling.

    Added after a fidelity check: deleting constraint (3) left the suite green,
    because in every other test case constraint (1) happened to bind first.
    """
    sizes = {"big1": 10, "big2": 10, "t1": 1, "t2": 1, "t3": 1}

    result = solve_group_feasibility(sizes, make_config(target_coverage=5))

    assert result.coverage == 3  # 23 students − 10 − 10
    assert result.workload <= make_config().max_workload
    assert result.reduced is True
    assert "3" in result.reason


def test_max_workload_caps_coverage_even_when_the_room_is_large(large_classroom):
    # Constraint (2): the student time budget wins over the coverage target.
    result = solve_group_feasibility(
        _sizes(large_classroom), make_config(target_coverage=20, max_workload=1)
    )

    assert result.workload <= 1
    assert result.coverage < 20


def test_a_single_group_cannot_be_compared_against_anything():
    with pytest.raises(PairingInfeasibleError):
        solve_group_feasibility({"g1": 5}, make_config())


def test_a_two_group_classroom_is_refused_because_nobody_is_eligible_to_judge():
    """OQ-8: with two groups, every student sits inside the only pair.

    Constraint (1) catches it — ``P − (N − 1)`` is zero, so no student has a
    single pair they are allowed to judge.
    """
    with pytest.raises(PairingInfeasibleError):
        solve_group_feasibility({"g1": 5, "g2": 5}, make_config())


def test_an_empty_classroom_is_rejected_rather_than_producing_zero_pairs():
    with pytest.raises(PairingInfeasibleError):
        solve_group_feasibility({"g1": 0, "g2": 0}, make_config())


# ---------------------------------------------------------------------------
# §8.4 — allocation and invariants
# ---------------------------------------------------------------------------


def test_no_evaluator_is_ever_asked_to_judge_their_own_group(small_classroom):
    """INV-1 / FR-PAIR-02."""
    pairs = generate_group_pairs(
        small_classroom, make_criterion(), make_config(), "a1"
    )
    own_group = {student.id: student.group_id for student in small_classroom}

    for pair in pairs:
        assert own_group[pair.evaluator_id] not in pair.key


def test_no_evaluator_receives_the_same_pair_twice_in_one_criterion(large_classroom):
    """INV-2 / FR-PAIR-07 — repeating a pair adds no statistical information."""
    pairs = generate_group_pairs(
        large_classroom, make_criterion(), make_config(), "a1"
    )
    seen = [(pair.evaluator_id, pair.key) for pair in pairs]

    assert len(seen) == len(set(seen))


def test_coverage_is_balanced_across_every_pair(large_classroom):
    """INV-3 / FR-PAIR-06."""
    pairs = generate_group_pairs(
        large_classroom, make_criterion(), make_config(), "a1"
    )
    counts = coverage_by_pair(pairs).values()

    assert max(counts) - min(counts) <= 1


def test_workload_is_balanced_across_every_evaluator(large_classroom):
    """INV-4 — nobody gets double the reviewing their neighbour got."""
    pairs = generate_group_pairs(
        large_classroom, make_criterion(), make_config(), "a1"
    )
    counts = workload_by_evaluator(pairs).values()

    assert max(counts) - min(counts) <= 1


def test_the_same_seed_reproduces_the_identical_allocation(large_classroom):
    """INV-5 / FR-PAIR-09 — without this, no pairing bug can be reproduced."""
    config = make_config(pairing_seed=4242)

    first = generate_group_pairs(large_classroom, make_criterion(), config, "a1")
    second = generate_group_pairs(large_classroom, make_criterion(), config, "a1")

    assert first == second


def test_a_different_seed_produces_a_different_allocation(large_classroom):
    a = generate_group_pairs(
        large_classroom, make_criterion(), make_config(pairing_seed=1), "a1"
    )
    b = generate_group_pairs(
        large_classroom, make_criterion(), make_config(pairing_seed=2), "a1"
    )

    assert a != b


def test_each_pair_records_which_item_was_shown_on_the_left(large_classroom):
    """FR-PAIR-08 / D8."""
    pairs = generate_group_pairs(
        large_classroom, make_criterion(), make_config(), "a1"
    )

    for pair in pairs:
        assert pair.display_left_item_id in pair.key
        assert pair.display_right_item_id in pair.key
        assert pair.display_left_item_id != pair.display_right_item_id

    # Over 225 coin flips, an engine that never flipped would be obvious.
    left_is_a = sum(1 for pair in pairs if pair.display_left_item_id == pair.item_a_id)
    assert 0 < left_is_a < len(pairs)


def test_an_individual_criterion_is_refused_by_the_group_generator(small_classroom):
    with pytest.raises(ValueError):
        generate_group_pairs(
            small_classroom,
            make_criterion(side=Side.INDIVIDUAL),
            make_config(),
            "a1",
        )


# ---------------------------------------------------------------------------
# §8.3 — individual evaluation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "group_size, total_pairs, pairs_per_evaluator, coverage",
    [
        (3, 3, 1, 1),
        (4, 6, 3, 2),
        (5, 10, 6, 3),
        (6, 15, 10, 4),
        (7, 21, 15, 5),
    ],
)
def test_individual_plan_matches_the_table_in_the_prd(
    group_size, total_pairs, pairs_per_evaluator, coverage
):
    """§8.3 — coverage is m − 2, a consequence of group size, not a setting."""
    plan = individual_plan(group_size, make_config(max_workload=30))

    assert plan.total_pairs == total_pairs
    assert plan.pairs_per_evaluator == pairs_per_evaluator
    assert plan.coverage == coverage


@pytest.mark.parametrize("group_size", [0, 1, 2])
def test_groups_of_two_or_fewer_get_no_individual_evaluation(group_size):
    """FR-PAIR-12 — judging {a, b} needs a third person to do the judging."""
    plan = individual_plan(group_size, make_config())

    assert plan.enabled is False
    assert plan.coverage == 0


def test_a_group_of_three_is_always_flagged_low_confidence():
    """FR-PAIR-13 — one opinion per pair is not evidence."""
    plan = individual_plan(3, make_config())

    assert plan.enabled is True
    assert plan.low_confidence is True


def test_workload_cap_trims_pairs_and_reports_the_lower_coverage():
    """FR-PAIR-14 — a group of 8 would otherwise mean 21 pairs per person."""
    plan = individual_plan(8, make_config(max_workload=8))

    assert plan.pairs_per_evaluator == 8
    assert plan.coverage < 6
    assert "max_workload" in plan.note


def test_individual_pairs_never_include_the_evaluator_themselves():
    """FR-PAIR-03."""
    members = make_classroom(num_groups=1, group_size=5)
    pairs = generate_individual_pairs(
        members, make_criterion(side=Side.INDIVIDUAL), make_config(), "a1"
    )

    for pair in pairs:
        assert pair.evaluator_id not in pair.key


def test_individual_pairs_stay_inside_a_single_group():
    members = make_classroom(num_groups=1, group_size=5)
    pairs = generate_individual_pairs(
        members, make_criterion(side=Side.INDIVIDUAL), make_config(), "a1"
    )
    member_ids = {member.id for member in members}

    for pair in pairs:
        assert pair.key <= member_ids


def test_individual_generation_satisfies_every_invariant():
    members = make_classroom(num_groups=1, group_size=6)
    pairs = generate_individual_pairs(
        members, make_criterion(side=Side.INDIVIDUAL), make_config(max_workload=30), "a1"
    )

    check_invariants(pairs, {member.id: member.id for member in members})


def test_mixing_groups_in_an_individual_generation_is_rejected():
    members = make_classroom(num_groups=2, group_size=3)

    with pytest.raises(ValueError):
        generate_individual_pairs(
            members, make_criterion(side=Side.INDIVIDUAL), make_config(), "a1"
        )
