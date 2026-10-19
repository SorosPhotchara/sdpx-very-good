"""Allocate eligible evaluators to pairwise comparisons."""

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from random import Random
from typing import Literal, Mapping, Sequence

MINIMUM_PAIRS_PER_EVALUATOR = 1


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
    initial_loads: Mapping[int, int] | None = None,
    minimum: int = MINIMUM_PAIRS_PER_EVALUATOR,
) -> list[PairAllocation]:
    if coverage < 1:
        raise ValueError("Coverage must be positive")
    if minimum < 0:
        raise ValueError("Minimum must not be negative")

    random = Random(seed)
    work = list(combinations(pair_items, 2))
    random.shuffle(work)
    evaluator_order = list(dict.fromkeys(
        evaluator_id
        for item_evaluators in evaluators.values()
        for evaluator_id in item_evaluators
    ))
    random.shuffle(evaluator_order)
    # Loads carry work from earlier criteria so coverage stays balanced across them,
    # while issued counts this call alone, which is what the minimum applies to.
    loads = {
        evaluator_id: (initial_loads or {}).get(evaluator_id, 0)
        for evaluator_id in evaluator_order
    }
    issued: Counter[int] = Counter()
    work_index = {pair: index for index, pair in enumerate(work)}
    eligibility: dict[tuple[int, int], set[int]] = {}
    assigned: dict[tuple[int, int], set[int]] = {}
    allocations: list[PairAllocation] = []

    for left_id, right_id in work:
        excluded = set(evaluators[left_id]) | set(evaluators[right_id]) if kind == "group" else {left_id, right_id}
        eligible = [evaluator_id for evaluator_id in evaluator_order if evaluator_id not in excluded]
        if not eligible:
            raise ValueError("No eligible evaluator for a pair")
        eligibility[(left_id, right_id)] = set(eligible)
        assigned[(left_id, right_id)] = set()
        for _ in range(min(coverage, len(eligible))):
            evaluator_id = min(eligible, key=loads.__getitem__)
            eligible.remove(evaluator_id)
            loads[evaluator_id] += 1
            issued[evaluator_id] += 1
            assigned[(left_id, right_id)].add(evaluator_id)
            allocations.append(PairAllocation(kind, left_id, right_id, evaluator_id))

    # Coverage leaves evaluators idle whenever the pairs offer fewer slots than there
    # are evaluators, so give everyone this call skipped the least covered pair left.
    for evaluator_id in evaluator_order:
        while issued[evaluator_id] < minimum:
            candidates = [
                pair for pair in work
                if evaluator_id in eligibility[pair] and evaluator_id not in assigned[pair]
            ]
            if not candidates:
                break
            pair = min(candidates, key=lambda item: (len(assigned[item]), work_index[item]))
            assigned[pair].add(evaluator_id)
            loads[evaluator_id] += 1
            issued[evaluator_id] += 1
            allocations.append(PairAllocation(kind, pair[0], pair[1], evaluator_id))

    return allocations


def allocate_group_pairs(
    groups: Mapping[int, Sequence[int]], coverage: int = 5, seed: int | None = None,
    initial_loads: Mapping[int, int] | None = None,
    minimum: int = MINIMUM_PAIRS_PER_EVALUATOR,
) -> list[PairAllocation]:
    active = {group_id: members for group_id, members in groups.items() if members}
    if len(active) < 3:
        raise ValueError("At least three non-empty groups are required")
    members = [student_id for group_members in active.values() for student_id in group_members]
    if len(members) != len(set(members)):
        raise ValueError("A student cannot belong to multiple groups in one classroom")
    return _allocate("group", list(active), active, coverage, seed, initial_loads, minimum)


def allocate_individual_pairs(
    members: Sequence[int], coverage: int = 5, seed: int | None = None,
    initial_loads: Mapping[int, int] | None = None,
    minimum: int = MINIMUM_PAIRS_PER_EVALUATOR,
) -> list[PairAllocation]:
    if len(members) != len(set(members)):
        raise ValueError("Group members must be distinct")
    if len(members) < 3:
        return []
    return _allocate(
        "individual", members, {member: members for member in members},
        coverage, seed, initial_loads, minimum,
    )
