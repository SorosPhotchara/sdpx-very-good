"""Scoring engine tests (PRD §9).

Test names state the rule they protect: when one goes red, the name says which
part of §9 stopped being true.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain import ComparisonStatus, Flag, Side
from app.scoring import (
    SIX_POINT_SCALE,
    Participation,
    ScoringError,
    compute_component,
    compute_quality_index,
    final_personal_score,
    participation_multiplier,
    points_for_items,
    quantize,
    score_ratio,
    validate_criteria_weights,
    weighted_criterion_score,
)
from tests.factories import (
    make_comparison,
    make_config,
    make_criterion,
    make_pair,
    make_participation,
)


# ---------------------------------------------------------------------------
# §9.1 — one comparison to points
# ---------------------------------------------------------------------------


def test_every_choice_splits_exactly_one_point_between_the_two_items():
    for choice, (left, right) in SIX_POINT_SCALE.items():
        assert left + right == Decimal("1"), f"choice {choice} does not sum to 1"


def test_scale_has_no_neutral_option_so_no_choice_splits_the_point_evenly():
    # D1: a middle button is what evaluators press to avoid deciding.
    assert not any(
        left == right for left, right in SIX_POINT_SCALE.values()
    ), "a 50/50 option would reintroduce central tendency bias"


def test_points_follow_the_displayed_position_not_the_stored_item_order():
    # FR-PAIR-08 randomises which item is on the left; §9.1 has to replay it.
    shown_a_left = make_comparison(
        pair=make_pair(item_a_id="g1", item_b_id="g2", display_left_item_id="g1"),
        choice=1,  # "left much better"
    )
    shown_b_left = make_comparison(
        pair=make_pair(item_a_id="g1", item_b_id="g2", display_left_item_id="g2"),
        choice=1,
    )

    assert points_for_items(shown_a_left)["g1"] == Decimal("1.0")
    assert points_for_items(shown_b_left)["g1"] == Decimal("0.0")


# ---------------------------------------------------------------------------
# §9.2 — quality index
# ---------------------------------------------------------------------------


def test_quality_index_is_the_weighted_mean_of_the_points_an_item_received():
    criterion = make_criterion(id="ux")
    # 0.8 × 3 + 0.6 × 2 = 3.6 over 5 comparisons → q = 0.72 (the §9.5 figure).
    comparisons = [
        make_comparison(
            pair=make_pair(
                criterion_id="ux", item_a_id="g1", item_b_id=f"g{n}",
                display_left_item_id="g1",
            ),
            choice=choice,
        )
        for n, choice in enumerate((2, 2, 2, 3, 3), start=2)
    ]

    quality = compute_quality_index("g1", criterion, comparisons, make_config())

    assert quality.value == Decimal("0.72")
    assert quality.comparison_count == 5


def test_draft_and_excluded_comparisons_never_reach_a_score():
    # DR-01. A draft is a student thinking out loud, not an answer.
    criterion = make_criterion(id="ux")
    pair = make_pair(criterion_id="ux", display_left_item_id="g1")
    comparisons = [
        make_comparison(pair=pair, choice=1, status=ComparisonStatus.SUBMITTED),
        make_comparison(pair=pair, choice=6, status=ComparisonStatus.DRAFT),
        make_comparison(pair=pair, choice=6, status=ComparisonStatus.EXCLUDED),
    ]

    quality = compute_quality_index("g1", criterion, comparisons, make_config())

    assert quality.comparison_count == 1
    assert quality.value == Decimal("1.0")


def test_instructor_weight_shifts_the_mean_without_inflating_the_comparison_count():
    # D6: influence rides in w, not in duplicated votes.
    criterion = make_criterion(id="ux")
    pair = make_pair(criterion_id="ux", display_left_item_id="g1")
    comparisons = [
        make_comparison(pair=pair, choice=6, evaluator_weight=Decimal("1.0")),  # 0.0
        make_comparison(pair=pair, choice=1, evaluator_weight=Decimal("3.0")),  # 1.0
    ]

    quality = compute_quality_index("g1", criterion, comparisons, make_config())

    assert quality.value == Decimal("0.75")  # (0×1 + 1×3) / 4
    assert quality.comparison_count == 2


def test_item_below_min_comparisons_is_flagged_low_confidence():
    # FR-SCORE-05: two opinions are not enough to defend in an appeal.
    criterion = make_criterion(id="ux")
    pair = make_pair(criterion_id="ux", display_left_item_id="g1")
    comparisons = [make_comparison(pair=pair, choice=1) for _ in range(2)]

    quality = compute_quality_index(
        "g1", criterion, comparisons, make_config(min_comparisons=3)
    )

    assert quality.is_low_confidence


def test_item_with_no_comparisons_has_no_quality_index_rather_than_zero():
    criterion = make_criterion(id="ux")

    quality = compute_quality_index("g-unseen", criterion, [], make_config())

    assert quality.value is None
    assert quality.comparison_count == 0


# ---------------------------------------------------------------------------
# §9.3 — band mapping
# ---------------------------------------------------------------------------


def test_band_mapping_puts_q_zero_at_the_floor_and_q_one_at_the_ceiling():
    config = make_config()  # floor 0.600, ceiling 1.000

    assert score_ratio(Decimal("0"), config) == Decimal("0.600")
    assert score_ratio(Decimal("1"), config) == Decimal("1.000")
    assert score_ratio(Decimal("0.5"), config) == Decimal("0.800")


def test_band_mapping_never_normalises_scores_to_sum_to_one():
    # D2: ten groups each scoring q=0.5 must each land at 80%, not at 1/10.
    config = make_config()
    ratios = [score_ratio(Decimal("0.5"), config) for _ in range(10)]

    assert all(ratio == Decimal("0.800") for ratio in ratios)
    assert sum(ratios) == Decimal("8.000")


def test_quality_index_outside_zero_to_one_is_rejected_rather_than_clamped():
    with pytest.raises(ScoringError):
        score_ratio(Decimal("1.4"), make_config())


def test_criteria_weights_must_total_one_hundred_percent(individual_criteria):
    # FR-ASSIGN-02.
    broken = [
        make_criterion(id="a", weight_pct=Decimal("40")),
        make_criterion(id="b", weight_pct=Decimal("40")),
    ]

    with pytest.raises(ScoringError):
        validate_criteria_weights(broken, Side.GROUP)

    validate_criteria_weights(individual_criteria, Side.INDIVIDUAL)  # 50 + 50


def test_a_side_with_no_criteria_is_switched_off_rather_than_invalid():
    # FR-ASSIGN-07: individual_max_score = 0 means that half does not exist.
    validate_criteria_weights([], Side.INDIVIDUAL)


# ---------------------------------------------------------------------------
# §9.5 — golden test from the PRD worked example
# ---------------------------------------------------------------------------

AURORA_GROUP = [
    # (criterion weight %, q, expected score_ratio, expected weighted score)
    (Decimal("40"), Decimal("0.72"), Decimal("0.888"), Decimal("5.328")),
    (Decimal("35"), Decimal("0.55"), Decimal("0.820"), Decimal("4.305")),
    (Decimal("25"), Decimal("0.61"), Decimal("0.844"), Decimal("3.165")),
]

NOK_INDIVIDUAL = [
    (Decimal("50"), Decimal("0.68"), Decimal("0.872"), Decimal("2.180")),
    (Decimal("50"), Decimal("0.45"), Decimal("0.780"), Decimal("1.950")),
]

TON_INDIVIDUAL = [
    (Decimal("50"), Decimal("0.31"), Decimal("0.724"), Decimal("1.810")),
    (Decimal("50"), Decimal("0.35"), Decimal("0.740"), Decimal("1.850")),
]


def _component(rows, max_score_side):
    config = make_config()
    total = Decimal("0")
    for weight_pct, quality, expected_ratio, expected_weighted in rows:
        ratio = score_ratio(quality, config)
        assert ratio == expected_ratio
        weighted = weighted_criterion_score(
            ratio, make_criterion(weight_pct=weight_pct), max_score_side
        )
        assert weighted == expected_weighted
        total += weighted
    return total


def test_golden_group_aurora_scores_12_798_out_of_15():
    assert _component(AURORA_GROUP, Decimal("15")) == Decimal("12.798")


def test_golden_student_nok_who_evaluated_everything_scores_16_93_out_of_20():
    group = _component(AURORA_GROUP, Decimal("15"))
    individual = _component(NOK_INDIVIDUAL, Decimal("5"))
    assert individual == Decimal("4.130")

    participation = make_participation()  # 15 of 15
    multiplier = participation_multiplier(participation, make_config())
    assert multiplier == Decimal("1")

    total = final_personal_score(group, individual, multiplier)
    assert quantize(total) == Decimal("16.93")


def test_golden_student_ton_who_skipped_half_scores_10_97_out_of_20():
    group = _component(AURORA_GROUP, Decimal("15"))
    individual = _component(TON_INDIVIDUAL, Decimal("5"))
    assert individual == Decimal("3.660")

    # 6 of 12 group comparisons, 3 of 3 individual → p = 0.60, M = 0.667
    participation = make_participation(submitted_group=6, assigned_group=12)
    assert participation.ratio == Decimal("0.6")
    multiplier = participation_multiplier(participation, make_config())

    total = final_personal_score(group, individual, multiplier)
    assert quantize(total) == Decimal("10.97")


def test_a_members_missing_participation_does_not_reduce_the_group_score():
    # FR-SCORE-11 / D5, and the clearest thing in §9.5: Aurora still scores
    # 12.798 whether or not Ton reviewed anybody.
    engaged = _component(AURORA_GROUP, Decimal("15"))
    absent_member_multiplier = participation_multiplier(
        make_participation(submitted_group=0, assigned_group=12,
                           submitted_individual=0, assigned_individual=3),
        make_config(),
    )

    assert absent_member_multiplier == Decimal("0")
    assert engaged == Decimal("12.798")  # untouched by the multiplier above


# ---------------------------------------------------------------------------
# §9.4 — participation
# ---------------------------------------------------------------------------


def test_participation_at_or_above_the_threshold_gives_a_full_multiplier():
    config = make_config(completion_threshold=Decimal("0.900"))

    at_threshold = make_participation(submitted_group=9, assigned_group=10,
                                      submitted_individual=0, assigned_individual=0)
    assert participation_multiplier(at_threshold, config) == Decimal("1")

    above = make_participation(submitted_group=10, assigned_group=10,
                               submitted_individual=0, assigned_individual=0)
    assert participation_multiplier(above, config) == Decimal("1")


def test_a_student_who_was_assigned_nothing_is_not_penalised():
    # Members of a two-person group get no individual pairs at all (§8.3);
    # scoring them at zero would punish them for the engine's own limit.
    nothing_assigned = Participation(
        submitted_group=0, assigned_group=0,
        submitted_individual=0, assigned_individual=0,
    )

    assert nothing_assigned.ratio == Decimal("1")
    assert participation_multiplier(nothing_assigned, make_config()) == Decimal("1")


def test_submitting_more_than_assigned_is_rejected_as_impossible_data():
    with pytest.raises(ScoringError):
        Participation(
            submitted_group=5, assigned_group=3,
            submitted_individual=0, assigned_individual=0,
        )


# ---------------------------------------------------------------------------
# Component assembly
# ---------------------------------------------------------------------------


def test_component_sums_weighted_criteria_and_carries_flags_upward(group_criteria):
    comparisons = [
        make_comparison(
            pair=make_pair(
                criterion_id="ux", item_a_id="g1", item_b_id="g2",
                display_left_item_id="g1",
            ),
            choice=1,
        )
    ]

    component = compute_component(
        "g1", Side.GROUP, group_criteria, comparisons,
        Decimal("15"), make_config(),
    )

    # Only UX has evidence: 1.000 × 40% × 15 = 6.000
    assert component.total == Decimal("6.000")
    assert Flag.LOW_CONFIDENCE in component.flags


def test_criteria_belonging_to_the_other_side_are_ignored(
    group_criteria, individual_criteria
):
    component = compute_component(
        "g1", Side.GROUP, [*group_criteria, *individual_criteria], [],
        Decimal("15"), make_config(),
    )

    assert {row.criterion_id for row in component.per_criterion} == {
        "ux", "completeness", "innovation"
    }
