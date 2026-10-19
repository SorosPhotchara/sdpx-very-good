"""Convert pairwise votes into weighted relative scores."""

from dataclasses import dataclass
from typing import Sequence

POINTS = ((1.0, 0.0), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.0, 1.0))


@dataclass(frozen=True)
class PairVote:
    left_id: int
    right_id: int
    choice: int
    weight: float = 1.0


@dataclass(frozen=True)
class ItemScore:
    average_points: float | None
    relative_score: float | None
    weighted_score: float | None
    effective_votes: float


def score_items(
    item_ids: Sequence[int],
    votes: Sequence[PairVote],
    max_score: float,
    criterion_weight: float,
    final: bool = False,
) -> dict[int, ItemScore]:
    if max_score < 0 or not 0 <= criterion_weight <= 1:
        raise ValueError("Score maximum and criterion weight must be valid")
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("Items must be distinct")

    points = {item_id: 0.0 for item_id in item_ids}
    effective_votes = {item_id: 0.0 for item_id in item_ids}
    for vote in votes:
        if vote.left_id == vote.right_id or vote.left_id not in points or vote.right_id not in points:
            raise ValueError("Vote refers to an invalid pair")
        if not 1 <= vote.choice <= 5 or vote.weight <= 0:
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
    total_average = sum(averages.values())
    result: dict[int, ItemScore] = {}
    for item_id in item_ids:
        average = averages.get(item_id)
        if average is None:
            result[item_id] = ItemScore(
                average_points=None,
                relative_score=0.0 if final else None,
                weighted_score=0.0 if final else None,
                effective_votes=0.0,
            )
            continue
        relative = average / total_average
        result[item_id] = ItemScore(
            average_points=average,
            relative_score=relative,
            weighted_score=relative * criterion_weight * max_score,
            effective_votes=effective_votes[item_id],
        )
    return result
