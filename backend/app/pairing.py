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
    flipped: bool = False


def _allocate(
    kind: Literal["group", "individual"],
    pair_items: Sequence[int],
    evaluators: Mapping[int, Sequence[int]],
    coverage: int,
    seed: int | None,
    initial_loads: Mapping[int, int] | None = None,
    minimum: int = MINIMUM_PAIRS_PER_EVALUATOR,
    max_workload: int | None = None,
) -> list[PairAllocation]:
    if coverage < 1:
        raise ValueError("Coverage must be positive")
    if minimum < 0:
        raise ValueError("Minimum must not be negative")
    if max_workload is not None and max_workload < 1:
        raise ValueError("Max workload must be positive")

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

    for left_id, right_id in work:
        excluded = set(evaluators[left_id]) | set(evaluators[right_id]) if kind == "group" else {left_id, right_id}
        eligible = [evaluator_id for evaluator_id in evaluator_order if evaluator_id not in excluded]
        if not eligible:
            raise ValueError("No eligible evaluator for a pair")
        eligibility[(left_id, right_id)] = set(eligible)
        assigned[(left_id, right_id)] = set()
        for _ in range(min(coverage, len(eligible))):
            # FR-PAIR-14: the workload ceiling wins over the coverage target, so
            # a pair takes fewer evaluators rather than overloading anyone.
            if max_workload is not None:
                eligible = [candidate for candidate in eligible
                            if issued[candidate] < max_workload]
                if not eligible:
                    break
            evaluator_id = min(eligible, key=loads.__getitem__)
            eligible.remove(evaluator_id)
            loads[evaluator_id] += 1
            issued[evaluator_id] += 1
            assigned[(left_id, right_id)].add(evaluator_id)

    # Coverage leaves evaluators idle whenever the pairs offer fewer slots than there
    # are evaluators, so give everyone this call skipped the least covered pair left.
    # This is the one thing allowed to push a pair past the coverage target: an
    # evaluator with nothing to open is worse than an unevenly covered pair.
    for evaluator_id in evaluator_order:
        while issued[evaluator_id] < minimum:
            if max_workload is not None and issued[evaluator_id] >= max_workload:
                break
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

    _balance_workload(work, work_index, eligibility, assigned, loads, issued,
                      evaluator_order, max_workload)

    # Built last so balancing cannot leave a stale allocation behind, and in a
    # deterministic order so the same seed reproduces the same display flips
    # (INV-5).
    return [
        PairAllocation(kind, pair[0], pair[1], evaluator_id, random.getrandbits(1) == 1)
        for pair in sorted(work, key=work_index.__getitem__)
        for evaluator_id in sorted(assigned[pair],
                                   key=lambda item: evaluator_order.index(item))
    ]


def _balance_workload(
    work: list[tuple[int, int]],
    work_index: Mapping[tuple[int, int], int],
    eligibility: Mapping[tuple[int, int], set[int]],
    assigned: dict[tuple[int, int], set[int]],
    loads: dict[int, int],
    issued: Counter[int],
    evaluator_order: Sequence[int],
    max_workload: int | None,
) -> None:
    """Even out pairs per evaluator until no two differ by more than one (INV-4).

    Each step hands one pair from a busiest evaluator to an idlest one that is
    eligible for it, which leaves that pair's coverage untouched. INV-1 to INV-3
    are therefore preserved, and the move strictly reduces the spread, so this
    terminates.
    """
    rank = {evaluator_id: index for index, evaluator_id in enumerate(evaluator_order)}
    ordered_work = sorted(work, key=work_index.__getitem__)
    # One move per unit of excess at most; the bound only guards against a logic
    # error becoming an endless loop.
    for _ in range(sum(issued.values()) + len(evaluator_order) + 1):
        counts = {evaluator_id: issued[evaluator_id] for evaluator_id in evaluator_order}
        if not counts:
            return
        busiest, idlest = max(counts.values()), min(counts.values())
        if busiest - idlest <= 1:
            return
        move = _find_move(ordered_work, eligibility, assigned, counts, rank,
                          busiest, idlest, max_workload)
        if move is None:
            return
        pair, over, under = move
        assigned[pair].discard(over)
        assigned[pair].add(under)
        for evaluator_id, delta in ((over, -1), (under, 1)):
            loads[evaluator_id] += delta
            issued[evaluator_id] += delta


def _find_move(
    ordered_work: Sequence[tuple[int, int]],
    eligibility: Mapping[tuple[int, int], set[int]],
    assigned: Mapping[tuple[int, int], set[int]],
    counts: Mapping[int, int],
    rank: Mapping[int, int],
    busiest: int,
    idlest: int,
    max_workload: int | None,
) -> tuple[tuple[int, int], int, int] | None:
    over_candidates = sorted((e for e, n in counts.items() if n == busiest), key=rank.__getitem__)
    under_candidates = sorted((e for e, n in counts.items() if n == idlest), key=rank.__getitem__)
    for under in under_candidates:
        if max_workload is not None and counts[under] >= max_workload:
            continue
        for pair in ordered_work:
            if under not in eligibility[pair] or under in assigned[pair]:
                continue
            for over in over_candidates:
                if over in assigned[pair]:
                    return pair, over, under
    return None


def allocate_group_pairs(
    groups: Mapping[int, Sequence[int]], coverage: int = 5, seed: int | None = None,
    initial_loads: Mapping[int, int] | None = None,
    minimum: int = MINIMUM_PAIRS_PER_EVALUATOR,
    max_workload: int | None = None,
) -> list[PairAllocation]:
    active = {group_id: members for group_id, members in groups.items() if members}
    if len(active) < 3:
        raise ValueError("At least three non-empty groups are required")
    members = [student_id for group_members in active.values() for student_id in group_members]
    if len(members) != len(set(members)):
        raise ValueError("A student cannot belong to multiple groups in one classroom")
    return _allocate("group", list(active), active, coverage, seed, initial_loads, minimum,
                     max_workload)


def allocate_individual_pairs(
    members: Sequence[int], coverage: int | None = None, seed: int | None = None,
    initial_loads: Mapping[int, int] | None = None,
    minimum: int = MINIMUM_PAIRS_PER_EVALUATOR,
    max_workload: int | None = None,
) -> list[PairAllocation]:
    """Allocate within one group.

    Coverage defaults to `m - 2`, which is complete enumeration: every member
    compares every pair that does not contain them (PRD D4, §8.3). Pass a
    smaller value only when a workload ceiling forces it.
    """
    if len(members) != len(set(members)):
        raise ValueError("Group members must be distinct")
    if len(members) < 3:
        return []
    return _allocate(
        "individual", members, {member: members for member in members},
        len(members) - 2 if coverage is None else coverage,
        seed, initial_loads, minimum, max_workload,
    )
