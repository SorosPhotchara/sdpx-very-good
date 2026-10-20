"""Convert pairwise votes into weighted scores via band mapping."""

from dataclasses import dataclass
from typing import Sequence

# 6-point forced choice (PRD D1, FR-EVAL-03, §9.1). No middle option: a tie
# invites central-tendency bias, so the scale has no "equal" answer.
POINTS = ((1.0, 0.0), (0.8, 0.2), (0.6, 0.4), (0.4, 0.6), (0.2, 0.8), (0.0, 1.0))
CHOICES = len(POINTS)

# Band mapping bounds (PRD D2, §9.3). Normalising scores to sum to one measured
# each item's share of the cohort rather than its quality: with ten groups every
# group landed near 1/10 of the section maximum, which is not a usable mark. The
# band maps the quality index onto [floor, ceiling] of the section instead, so a
# score means the same thing however many items are compared.
DEFAULT_SCORE_FLOOR = 0.6
DEFAULT_SCORE_CEILING = 1.0

# Share of their assigned comparisons a student must submit to keep all of their
# personal score (§9.4).
DEFAULT_COMPLETION_THRESHOLD = 0.9


@dataclass(frozen=True)
class PairVote:
    """One answer. ``left_id``/``right_id`` are the subjects as the evaluator saw
    them, so callers MUST apply ``Pair.display_flipped`` before building this."""

    left_id: int
    right_id: int
    choice: int
    weight: float = 1.0


@dataclass(frozen=True)
class ItemScore:
    average_points: float | None      # the quality index q, in [0, 1]
    score_ratio: float | None         # q mapped onto [floor, ceiling]
    weighted_score: float | None
    effective_votes: float


def score_items(
    item_ids: Sequence[int],
    votes: Sequence[PairVote],
    max_score: float,
    criterion_weight: float,
    final: bool = False,
    floor: float = DEFAULT_SCORE_FLOOR,
    ceiling: float = DEFAULT_SCORE_CEILING,
) -> dict[int, ItemScore]:
    if max_score < 0 or not 0 <= criterion_weight <= 1:
        raise ValueError("Score maximum and criterion weight must be valid")
    if not 0 <= floor < ceiling <= 1:
        raise ValueError("Score band needs 0 <= floor < ceiling <= 1")
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("Items must be distinct")

    points = {item_id: 0.0 for item_id in item_ids}
    effective_votes = {item_id: 0.0 for item_id in item_ids}
    for vote in votes:
        if vote.left_id == vote.right_id or vote.left_id not in points or vote.right_id not in points:
            raise ValueError("Vote refers to an invalid pair")
        if not 1 <= vote.choice <= CHOICES or vote.weight <= 0:
            raise ValueError("Vote choice and weight must be valid")
        left_points, right_points = POINTS[vote.choice - 1]
        points[vote.left_id] += left_points * vote.weight
        points[vote.right_id] += right_points * vote.weight
        effective_votes[vote.left_id] += vote.weight
        effective_votes[vote.right_id] += vote.weight

    averages = {
        item_id: points[item_id] / count
        for item_id, count in effective_votes.items()
        if count > 0
    }
    result: dict[int, ItemScore] = {}
    for item_id in item_ids:
        average = averages.get(item_id)
        if average is None:
            # No comparison is no evidence, which is not the same as the worst
            # evidence, so an unscored item sits outside the band rather than on
            # its floor: absent while the section is open, zero once it closes.
            result[item_id] = ItemScore(
                average_points=None,
                score_ratio=0.0 if final else None,
                weighted_score=0.0 if final else None,
                effective_votes=0.0,
            )
            continue
        ratio = floor + (ceiling - floor) * average
        result[item_id] = ItemScore(
            average_points=average,
            score_ratio=ratio,
            weighted_score=ratio * criterion_weight * max_score,
            effective_votes=effective_votes[item_id],
        )
    return result


def participation_multiplier(
    submitted: float, assigned: float,
    threshold: float = DEFAULT_COMPLETION_THRESHOLD,
) -> float:
    """How much of their earned score a student keeps, per PRD §9.4.

    Not evaluating peers says nothing about the quality of one's own work, so
    this is kept apart from the score itself (D5) and applied as a multiplier.
    It is capped at 1.0, so reaching the threshold is enough and there is no
    reward for exceeding it.
    """
    if not 0 < threshold <= 1:
        raise ValueError("Completion threshold must be within (0, 1]")
    if assigned <= 0:
        # Nothing was asked of them, so there is nothing to withhold.
        return 1.0
    return min(1.0, (submitted / assigned) / threshold)
