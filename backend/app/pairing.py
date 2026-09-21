"""Allocate eligible evaluators to pairwise comparisons."""

from dataclasses import dataclass
from itertools import combinations
from random import Random
from typing import Literal, Mapping, Sequence


@dataclass(frozen=True)
class PairAllocation:
    kind: Literal["group", "individual"]
    left_id: int
    right_id: int
    evaluator_id: int


def _allocate(
    kind: Literal["group", "individual"],
    pair_items: Sequence[int],
    evaluators: Mapping[int, Sequence[int]],
    coverage: int,
    seed: int | None,
) -> list[PairAllocation]:
    if coverage < 1:
        raise ValueError("Coverage must be positive")

    random = Random(seed)
    work = list(combinations(pair_items, 2)) * coverage
    random.shuffle(work)
    evaluator_order = list(dict.fromkeys(
        evaluator_id
        for item_evaluators in evaluators.values()
        for evaluator_id in item_evaluators
    ))
    random.shuffle(evaluator_order)
    loads = {evaluator_id: 0 for evaluator_id in evaluator_order}
    allocations: list[PairAllocation] = []

    for left_id, right_id in work:
        excluded = set(evaluators[left_id]) | set(evaluators[right_id]) if kind == "group" else {left_id, right_id}
        eligible = [evaluator_id for evaluator_id in evaluator_order if evaluator_id not in excluded]
        if not eligible:
            raise ValueError("No eligible evaluator for a pair")
        evaluator_id = min(eligible, key=loads.__getitem__)
        loads[evaluator_id] += 1
        allocations.append(PairAllocation(kind, left_id, right_id, evaluator_id))

    return allocations


def allocate_group_pairs(
    groups: Mapping[int, Sequence[int]], coverage: int = 5, seed: int | None = None
) -> list[PairAllocation]:
    active = {group_id: members for group_id, members in groups.items() if members}
    if len(active) < 3:
        raise ValueError("At least three non-empty groups are required")
    members = [student_id for group_members in active.values() for student_id in group_members]
    if len(members) != len(set(members)):
        raise ValueError("A student cannot belong to multiple groups in one classroom")
    return _allocate("group", list(active), active, coverage, seed)


def allocate_individual_pairs(
    members: Sequence[int], coverage: int = 5, seed: int | None = None
) -> list[PairAllocation]:
    if len(members) != len(set(members)):
        raise ValueError("Group members must be distinct")
    if len(members) < 3:
        return []
    return _allocate("individual", members, {member: members for member in members}, coverage, seed)
