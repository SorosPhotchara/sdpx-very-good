"""Scoring engine — turns comparisons into scores (PRD §9).

Pure functions over plain data (AR-01), so recomputing on the same rows gives
the same digits (FR-SCORE-10). ``Decimal`` throughout (DR-04).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Mapping, Sequence

from .domain import (
    AssignmentConfig,
    Comparison,
    ComparisonStatus,
    Criterion,
    Flag,
    Side,
)

#: The 6-point forced choice (D1/§9.1). No middle option, on purpose — a
#: neutral button is what evaluators press when they would rather not think,
#: and a column of neutral answers carries no information at all.
SIX_POINT_SCALE: Mapping[int, tuple[Decimal, Decimal]] = {
    1: (Decimal("1.0"), Decimal("0.0")),  # left much better
    2: (Decimal("0.8"), Decimal("0.2")),  # left better
    3: (Decimal("0.6"), Decimal("0.4")),  # left slightly better
    4: (Decimal("0.4"), Decimal("0.6")),  # right slightly better
    5: (Decimal("0.2"), Decimal("0.8")),  # right better
    6: (Decimal("0.0"), Decimal("1.0")),  # right much better
}


class ScoringError(Exception):
    """Raised when the inputs cannot produce a defensible score."""


# ---------------------------------------------------------------------------
# §9.1 — one comparison to points
# ---------------------------------------------------------------------------


def points_for_items(comparison: Comparison) -> dict[str, Decimal]:
    """Map a stored choice back onto the two items it was about.

    The choice was recorded against *screen positions*, and positions are
    randomised (FR-PAIR-08), so the displayed layout has to be replayed here.
    Reading ``choice`` without ``display_left_item_id`` inverts every
    comparison whose coin flip came up tails — and inverts it silently.
    """
    left_points, right_points = SIX_POINT_SCALE[comparison.choice]
    pair = comparison.pair
    return {
        pair.display_left_item_id: left_points,
        pair.display_right_item_id: right_points,
    }


# ---------------------------------------------------------------------------
# §9.2 — quality index
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QualityIndex:
    item_id: str
    criterion_id: str
    value: Decimal | None
    comparison_count: int
    effective_weight_sum: Decimal
    flags: tuple[Flag, ...] = ()

    @property
    def is_low_confidence(self) -> bool:
        return Flag.LOW_CONFIDENCE in self.flags


def compute_quality_index(
    item_id: str,
    criterion: Criterion,
    comparisons: Iterable[Comparison],
    config: AssignmentConfig,
) -> QualityIndex:
    """``q(i,c) = Σ(w × s) / Σ(w)`` over submitted comparisons (§9.2).

    Instructor influence rides in ``w`` as a float weight rather than as
    duplicated votes (D6), so the comparison count stays honest and the
    low-confidence check below keeps meaning what it says.
    """
    weighted_total = Decimal("0")
    weight_sum = Decimal("0")
    count = 0

    for comparison in comparisons:
        if comparison.status is not ComparisonStatus.SUBMITTED:
            continue  # DR-01: drafts and excluded rows never reach a grade
        if comparison.pair.criterion_id != criterion.id:
            continue
        points = points_for_items(comparison)
        if item_id not in points:
            continue

        weighted_total += comparison.evaluator_weight * points[item_id]
        weight_sum += comparison.evaluator_weight
        count += 1

    flags: list[Flag] = []
    if count < config.min_comparisons:
        # FR-SCORE-05: too thin to defend in an appeal. Flagged, not dropped —
        # the instructor decides what to do about it (FR-QS-01).
        flags.append(Flag.LOW_CONFIDENCE)

    value = None if weight_sum == 0 else weighted_total / weight_sum
    return QualityIndex(
        item_id=item_id,
        criterion_id=criterion.id,
        value=value,
        comparison_count=count,
        effective_weight_sum=weight_sum,
        flags=tuple(flags),
    )


# ---------------------------------------------------------------------------
# §9.3 — band mapping
# ---------------------------------------------------------------------------


def score_ratio(quality: Decimal, config: AssignmentConfig) -> Decimal:
    """``floor + (ceiling − floor) × q`` (§9.3, D2).

    Deliberately *not* normalised to sum to 1: with ten groups that hands each
    group ~0.1, which measures relative share rather than quality, and turns
    15 marks into 1.5 for everybody.
    """
    if not Decimal("0") <= quality <= Decimal("1"):
        raise ScoringError(f"quality index must be within [0, 1], got {quality}")
    return config.score_floor + (config.score_ceiling - config.score_floor) * quality


def weighted_criterion_score(
    ratio: Decimal, criterion: Criterion, max_score_side: Decimal
) -> Decimal:
    """``score_ratio × weight_c × max_score_side`` (§9.3)."""
    return ratio * (criterion.weight_pct / Decimal("100")) * max_score_side


def validate_criteria_weights(criteria: Sequence[Criterion], side: Side) -> None:
    """Criteria weights on one side must total 100% ± 0.01 (FR-ASSIGN-02)."""
    total = sum((c.weight_pct for c in criteria if c.side is side), start=Decimal("0"))
    if total == 0:
        return  # that side is switched off (FR-ASSIGN-07)
    if abs(total - Decimal("100")) > Decimal("0.01"):
        raise ScoringError(
            f"{side.value} criteria weights must total 100%, got {total}%"
        )


@dataclass(frozen=True)
class CriterionScore:
    criterion_id: str
    item_id: str
    quality_index: Decimal | None
    score_ratio: Decimal | None
    weighted_score: Decimal
    comparison_count: int
    flags: tuple[Flag, ...]


@dataclass(frozen=True)
class ComponentScore:
    item_id: str
    side: Side
    total: Decimal
    per_criterion: tuple[CriterionScore, ...]
    flags: tuple[Flag, ...]


def compute_component(
    item_id: str,
    side: Side,
    criteria: Sequence[Criterion],
    comparisons: Iterable[Comparison],
    max_score_side: Decimal,
    config: AssignmentConfig,
) -> ComponentScore:
    """Sum one item's weighted criterion scores for one side (§9.3)."""
    comparisons = list(comparisons)
    validate_criteria_weights(criteria, side)

    rows: list[CriterionScore] = []
    total = Decimal("0")
    flags: set[Flag] = set()

    for criterion in criteria:
        if criterion.side is not side:
            continue
        quality = compute_quality_index(item_id, criterion, comparisons, config)
        flags.update(quality.flags)

        if quality.value is None:
            # No evidence at all. Contribute nothing rather than inventing a
            # floor score for work that nobody actually judged.
            rows.append(
                CriterionScore(
                    criterion_id=criterion.id,
                    item_id=item_id,
                    quality_index=None,
                    score_ratio=None,
                    weighted_score=Decimal("0"),
                    comparison_count=quality.comparison_count,
                    flags=quality.flags,
                )
            )
            continue

        ratio = score_ratio(quality.value, config)
        weighted = weighted_criterion_score(ratio, criterion, max_score_side)
        total += weighted
        rows.append(
            CriterionScore(
                criterion_id=criterion.id,
                item_id=item_id,
                quality_index=quality.value,
                score_ratio=ratio,
                weighted_score=weighted,
                comparison_count=quality.comparison_count,
                flags=quality.flags,
            )
        )

    return ComponentScore(
        item_id=item_id,
        side=side,
        total=total,
        per_criterion=tuple(rows),
        flags=tuple(sorted(flags, key=lambda flag: flag.value)),
    )


# ---------------------------------------------------------------------------
# §9.4 — participation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Participation:
    submitted_group: int
    assigned_group: int
    submitted_individual: int
    assigned_individual: int

    def __post_init__(self) -> None:
        counts = (
            self.submitted_group,
            self.assigned_group,
            self.submitted_individual,
            self.assigned_individual,
        )
        if min(counts) < 0:
            raise ScoringError("comparison counts must not be negative")
        if self.submitted_group > self.assigned_group:
            raise ScoringError("submitted group comparisons exceed assigned")
        if self.submitted_individual > self.assigned_individual:
            raise ScoringError("submitted individual comparisons exceed assigned")

    @property
    def ratio(self) -> Decimal:
        """``p`` — submitted over assigned, pooled across both sides (§9.4)."""
        assigned = self.assigned_group + self.assigned_individual
        if assigned == 0:
            # Nothing was asked of this student, so nothing can be withheld.
            # Returning 0 here would punish members of two-person groups for a
            # limit the pairing engine imposed on them (§8.3).
            return Decimal("1")
        submitted = self.submitted_group + self.submitted_individual
        return Decimal(submitted) / Decimal(assigned)


def participation_multiplier(
    participation: Participation, config: AssignmentConfig
) -> Decimal:
    """``M = min(1, p / completion_threshold)`` (§9.4).

    Kept apart from the quality index on purpose (D5): not reviewing your peers
    is a participation failure, not evidence that your own work was bad.
    """
    return min(Decimal("1"), participation.ratio / config.completion_threshold)


def final_personal_score(
    group_component: Decimal,
    individual_component: Decimal,
    multiplier: Decimal,
) -> Decimal:
    """``(group + individual) × M`` (§9.4).

    Note what is *absent*: the group's own recorded score never passes through
    here, so one member's silence cannot dock their teammates (FR-SCORE-11).
    """
    if multiplier < 0:
        raise ScoringError("participation multiplier must not be negative")
    return (group_component + individual_component) * multiplier


def quantize(value: Decimal, places: str = "0.01") -> Decimal:
    """Round for display only. Storage keeps full precision (FR-SCORE-09)."""
    return value.quantize(Decimal(places))
