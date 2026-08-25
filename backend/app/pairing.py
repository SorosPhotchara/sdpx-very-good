"""Pairing engine — decides who compares which pair (PRD §8).

Two rules drive everything here:

* Coverage ``R`` and workload ``k`` are computed *from each other*, never both
  fixed (D3). Fixing both is what made the v1.2 spec infeasible for small rooms.
* When the requested coverage cannot be met, the engine lowers it and says so
  in numbers (FR-PAIR-05). It never degrades silently, and it never asks an
  evaluator to judge the same pair twice to pad the count (FR-PAIR-07).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from collections import deque
from itertools import combinations
from math import ceil, comb
from random import Random
from typing import Callable, Iterable, Mapping, Sequence

from .domain import (
    AssignmentConfig,
    Criterion,
    Feasibility,
    PairAssignment,
    PairingInfeasibleError,
    Side,
    Student,
)


def seeded_rng(*parts: object) -> Random:
    """A reproducible RNG (INV-5).

    Python's builtin ``hash()`` is salted per process, so seeding from it would
    make pairing unreproducible between runs — which would take FR-PAIR-09 and
    every "reproduce the bug" request with it. Hash the parts explicitly.
    """
    material = "|".join(str(part) for part in parts).encode("utf-8")
    return Random(int.from_bytes(hashlib.sha256(material).digest(), "big"))


# ---------------------------------------------------------------------------
# Group evaluation
# ---------------------------------------------------------------------------


def solve_group_feasibility(
    group_sizes: Mapping[str, int], config: AssignmentConfig
) -> Feasibility:
    """Find the highest coverage satisfying all three constraints in §8.2.

    ::

        P            = C(N, 2)
        slots_needed = P × R
        k            = ceil(slots_needed / S)

        (1) k ≤ P − (N − 1)                        evaluator skips own group
        (2) k ≤ k_max                              time budget per student
        (3) R ≤ min over pairs of (S − |a| − |b|)  who may judge that pair

    Raises:
        PairingInfeasibleError: if not even coverage 1 is reachable.
    """
    if any(size < 0 for size in group_sizes.values()):
        raise ValueError("group sizes must not be negative")

    num_groups = len(group_sizes)
    num_students = sum(group_sizes.values())

    if num_groups < 2:
        raise PairingInfeasibleError(
            "ต้องมีอย่างน้อย 2 กลุ่มจึงจะเปรียบเทียบแบบ pairwise ได้"
        )
    if num_students == 0:
        raise PairingInfeasibleError("ไม่มีนักศึกษาใน classroom นี้")

    possible_pairs = comb(num_groups, 2)
    eligible_pairs_per_evaluator = possible_pairs - (num_groups - 1)
    raters_per_pair = min(
        num_students - group_sizes[a] - group_sizes[b]
        for a, b in combinations(sorted(group_sizes), 2)
    )

    blockers: list[str] = []
    for coverage in range(config.target_coverage, 0, -1):
        slots_needed = possible_pairs * coverage
        workload = ceil(slots_needed / num_students)

        if workload > eligible_pairs_per_evaluator:
            blockers.append(
                f"R={coverage}: ต้องประเมิน {workload} คู่/คน "
                f"แต่แต่ละคนมีคู่ที่ประเมินได้เพียง {eligible_pairs_per_evaluator} คู่"
            )
            continue
        if workload > config.max_workload:
            blockers.append(
                f"R={coverage}: ต้องประเมิน {workload} คู่/คน "
                f"เกินเพดาน max_workload={config.max_workload}"
            )
            continue
        if coverage > raters_per_pair:
            blockers.append(
                f"R={coverage}: แต่ละคู่มีผู้มีสิทธิ์ประเมินเพียง {raters_per_pair} คน"
            )
            continue

        reduced = coverage < config.target_coverage
        if reduced:
            # FR-PAIR-05: say it in numbers. "Coverage was lowered" with no
            # figures is the kind of warning everyone learns to click past.
            reason = (
                f"ห้องนี้มี {num_groups} กลุ่ม แต่ละคู่มีผู้มีสิทธิ์ประเมินเพียง "
                f"{raters_per_pair} คน จึงตั้ง coverage ได้สูงสุด {coverage} ครั้งต่อคู่ "
                f"(ไม่ใช่ {config.target_coverage} ตามค่าตั้งต้น) "
                f"นักศึกษาแต่ละคนจะได้ {workload} คู่ต่อเกณฑ์"
            )
        else:
            reason = (
                f"coverage {coverage} ครั้งต่อคู่ ตามค่าตั้งต้น "
                f"นักศึกษาแต่ละคนจะได้ {workload} คู่ต่อเกณฑ์"
            )

        return Feasibility(
            coverage=coverage,
            workload=workload,
            total_comparisons=slots_needed,
            reduced=reduced,
            reason=reason,
            possible_pairs=possible_pairs,
            notes=blockers,
        )

    raise PairingInfeasibleError(
        "ไม่มี coverage ที่เป็นไปได้สำหรับ classroom นี้: " + " · ".join(blockers)
    )


def generate_group_pairs(
    students: Sequence[Student],
    criterion: Criterion,
    config: AssignmentConfig,
    assignment_id: str,
) -> list[PairAssignment]:
    """Assign group-vs-group comparisons (FR-PAIR-01/02/06/07/08)."""
    if criterion.side is not Side.GROUP:
        raise ValueError("generate_group_pairs expects a GROUP criterion")
    if not students:
        raise PairingInfeasibleError("ไม่มีนักศึกษาใน classroom นี้")

    group_sizes: dict[str, int] = {}
    for student in students:
        group_sizes[student.group_id] = group_sizes.get(student.group_id, 0) + 1

    feasibility = solve_group_feasibility(group_sizes, config)
    all_pairs = [frozenset(pair) for pair in combinations(sorted(group_sizes), 2)]

    for coverage in range(feasibility.coverage, 0, -1):
        rng = seeded_rng(config.pairing_seed, assignment_id, criterion.id, coverage)
        pairs = _allocate(
            students=students,
            all_pairs=all_pairs,
            coverage=coverage,
            criterion=criterion,
            side=Side.GROUP,
            rng=rng,
            item_of=lambda student: student.group_id,
        )
        if pairs is not None:
            return pairs

    raise PairingInfeasibleError(
        "จัดสรร pair ไม่สำเร็จแม้ลด coverage ลงถึง 1 — ตรวจขนาดกลุ่มและจำนวนนักศึกษา"
    )


# ---------------------------------------------------------------------------
# Individual evaluation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IndividualPlan:
    """Complete-enumeration numbers for a group of ``m`` members (§8.3)."""

    group_size: int
    total_pairs: int
    pairs_per_evaluator: int
    coverage: int
    enabled: bool
    low_confidence: bool
    note: str


def individual_plan(group_size: int, config: AssignmentConfig) -> IndividualPlan:
    """Describe individual evaluation inside a group of ``m`` members.

    A pair ``{a, b}`` inside a group can only be judged by the other ``m − 2``
    members, so coverage is a *consequence of group size* — not a target the
    instructor gets to pick (D4). Demanding coverage 5 from a group of 4 is
    arithmetically impossible, and v1.2 of the spec demanded exactly that.
    """
    if group_size < 0:
        raise ValueError("group_size must not be negative")

    total_pairs = comb(group_size, 2) if group_size >= 2 else 0
    ideal_pairs_per_evaluator = comb(group_size - 1, 2) if group_size >= 3 else 0
    coverage = max(0, group_size - 2)

    if group_size <= 2:
        return IndividualPlan(
            group_size=group_size,
            total_pairs=total_pairs,
            pairs_per_evaluator=0,
            coverage=0,
            enabled=False,
            low_confidence=False,
            note=(
                f"กลุ่มมีสมาชิก {group_size} คน — การเปรียบเทียบรายบุคคลต้องมีคนที่สาม"
                "เป็นผู้ประเมิน จึงไม่มีการประเมินรายบุคคลในกลุ่มนี้ (FR-PAIR-12)"
            ),
        )

    capped = ideal_pairs_per_evaluator > config.max_workload
    pairs_per_evaluator = min(ideal_pairs_per_evaluator, config.max_workload)
    if capped:
        # FR-PAIR-14: report the coverage actually reached, not the ideal one.
        coverage = (pairs_per_evaluator * group_size) // total_pairs

    note = (
        f"กลุ่ม {group_size} คน → {total_pairs} คู่ทั้งหมด, "
        f"{pairs_per_evaluator} คู่ต่อคน, coverage {coverage}"
    )
    if capped:
        note += (
            f" (ลดจาก {ideal_pairs_per_evaluator} คู่ต่อคน เพราะเกินเพดาน "
            f"max_workload={config.max_workload})"
        )
    if group_size == 3:
        note += " — coverage 1 ต่อคู่ ผลลัพธ์จะถูก flag LOW_CONFIDENCE เสมอ (FR-PAIR-13)"

    return IndividualPlan(
        group_size=group_size,
        total_pairs=total_pairs,
        pairs_per_evaluator=pairs_per_evaluator,
        coverage=coverage,
        enabled=True,
        low_confidence=group_size == 3,
        note=note,
    )


def generate_individual_pairs(
    members: Sequence[Student],
    criterion: Criterion,
    config: AssignmentConfig,
    assignment_id: str,
) -> list[PairAssignment]:
    """Enumerate within-group comparisons for one group (FR-PAIR-03/12/14)."""
    if criterion.side is not Side.INDIVIDUAL:
        raise ValueError("generate_individual_pairs expects an INDIVIDUAL criterion")

    group_ids = {member.group_id for member in members}
    if len(group_ids) > 1:
        raise ValueError("individual evaluation is scoped to a single group")

    plan = individual_plan(len(members), config)
    if not plan.enabled:
        return []

    rng = seeded_rng(config.pairing_seed, assignment_id, criterion.id, "individual")
    coverage_so_far: dict[frozenset[str], int] = {}
    pairs: list[PairAssignment] = []

    evaluators = sorted(members, key=lambda member: member.id)
    rng.shuffle(evaluators)

    for evaluator in evaluators:
        others = sorted(
            (member for member in members if member.id != evaluator.id),
            key=lambda member: member.id,
        )
        candidates = [frozenset((a.id, b.id)) for a, b in combinations(others, 2)]
        rng.shuffle(candidates)
        # Least-covered pairs first, so a cap trims the tail evenly (INV-3).
        candidates.sort(key=lambda key: coverage_so_far.get(key, 0))

        for key in candidates[: plan.pairs_per_evaluator]:
            coverage_so_far[key] = coverage_so_far.get(key, 0) + 1
            pairs.append(
                _build_pair(key, evaluator.id, criterion, Side.INDIVIDUAL, rng)
            )

    return pairs


# ---------------------------------------------------------------------------
# Invariants (PRD §8.4) — exported so tests and the API assert the same thing
# ---------------------------------------------------------------------------


def coverage_by_pair(pairs: Iterable[PairAssignment]) -> dict[frozenset[str], int]:
    counts: dict[frozenset[str], int] = {}
    for pair in pairs:
        counts[pair.key] = counts.get(pair.key, 0) + 1
    return counts


def workload_by_evaluator(pairs: Iterable[PairAssignment]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for pair in pairs:
        counts[pair.evaluator_id] = counts.get(pair.evaluator_id, 0) + 1
    return counts


def check_invariants(
    pairs: Sequence[PairAssignment], item_of: Mapping[str, str]
) -> None:
    """Assert INV-1 … INV-4. ``item_of`` maps evaluator id → their own item id.

    Raises:
        AssertionError: naming the invariant that broke and the data that broke it.
    """
    seen: set[tuple[str, str, frozenset[str]]] = set()
    for pair in pairs:
        own = item_of.get(pair.evaluator_id)
        assert own not in pair.key, (
            f"INV-1 broken: evaluator {pair.evaluator_id} was given pair "
            f"{sorted(pair.key)}, which contains their own item {own}"
        )
        fingerprint = (pair.evaluator_id, pair.criterion_id, pair.key)
        assert fingerprint not in seen, (
            f"INV-2 broken: evaluator {pair.evaluator_id} got pair "
            f"{sorted(pair.key)} twice in criterion {pair.criterion_id}"
        )
        seen.add(fingerprint)

    coverage = coverage_by_pair(pairs)
    if coverage:
        spread = max(coverage.values()) - min(coverage.values())
        assert spread <= 1, f"INV-3 broken: coverage spread is {spread}"

    # INV-4. Counted over every known evaluator, including those who drew no
    # pairs at all — otherwise a student the allocator forgot would simply be
    # absent from the tally instead of showing up as a zero.
    counts = workload_by_evaluator(pairs)
    loads = [counts.get(evaluator_id, 0) for evaluator_id in item_of]
    if loads:
        spread = max(loads) - min(loads)
        assert spread <= 1, f"INV-4 broken: workload spread is {spread}"


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _build_pair(
    key: frozenset[str],
    evaluator_id: str,
    criterion: Criterion,
    side: Side,
    rng: Random,
) -> PairAssignment:
    item_a, item_b = sorted(key)
    return PairAssignment(
        criterion_id=criterion.id,
        side=side,
        evaluator_id=evaluator_id,
        item_a_id=item_a,
        item_b_id=item_b,
        # D8/FR-PAIR-08: which item sits on the left is a coin flip, and it is
        # stored, because the raw choice means nothing without it.
        display_left_item_id=item_a if rng.random() < 0.5 else item_b,
    )


def _allocate(
    students: Sequence[Student],
    all_pairs: Sequence[frozenset[str]],
    coverage: int,
    criterion: Criterion,
    side: Side,
    rng: Random,
    item_of: Callable[[Student], str],
) -> list[PairAssignment] | None:
    """Fill ``coverage`` slots for every pair, or return ``None`` if stuck.

    Demand first, workload second: every pair is filled to exactly ``coverage``
    (INV-3, spread 0), and each slot goes to the *least loaded* evaluator who
    is still eligible for it, which keeps workload as even as the group sizes
    allow (INV-4).

    An earlier version handed out workload quotas up front and then filled
    pairs. That strands slots whenever group sizes differ: in a class of
    4 + 4 + 2, the pair {g1, g2} may only be judged by the two members of the
    small group, and the up-front quota can easily hand both of them zero. The
    property tests found it; ordering the two concerns the other way round
    removes the failure mode rather than patching it.
    """
    own_item = {student.id: item_of(student) for student in students}
    workload = {student.id: 0 for student in students}
    already: dict[str, set[frozenset[str]]] = {
        student.id: set() for student in students
    }

    pairs: list[PairAssignment] = []
    for _ in range(coverage):
        round_pairs = list(all_pairs)
        rng.shuffle(round_pairs)
        for key in round_pairs:
            candidates = [
                student
                for student in students
                if own_item[student.id] not in key  # INV-1
                and key not in already[student.id]  # INV-2
            ]
            if not candidates:
                return None  # caller retries at a lower coverage
            rng.shuffle(candidates)
            candidates.sort(key=lambda student: workload[student.id])
            chosen = candidates[0]

            workload[chosen.id] += 1
            already[chosen.id].add(key)
            pairs.append(_build_pair(key, chosen.id, criterion, side, rng))

    return _rebalance(pairs, own_item)


def _rebalance(
    pairs: list[PairAssignment], own_item: Mapping[str, str]
) -> list[PairAssignment]:
    """Even out workload after allocation, without touching coverage (INV-4).

    Greedy allocation cannot reach a spread of 1 on its own: late in a round,
    every lightly-loaded evaluator may already have judged the pair being
    handed out, so a heavier one takes it and the gap widens to 2.

    Handing one assignment straight from the busiest evaluator to the idlest is
    not enough either — it gets stuck whenever the idle evaluator's own group
    appears in all of the busy evaluator's pairs (INV-1 forbids the move even
    though a legal rearrangement exists). So this searches for an *augmenting
    chain* instead: busiest → intermediary → … → idlest, where each hop is a
    single legal handover. Everyone in the middle gives one away and takes one
    back, so only the two ends change load.

    Reassignment moves a comparison between evaluators, never between pairs, so
    INV-1, INV-2 and INV-3 all survive. Each chain shrinks the sum of squared
    workloads by a strictly positive amount, which is what makes the loop
    terminate.
    """
    workload: dict[str, int] = {evaluator_id: 0 for evaluator_id in own_item}
    judged: dict[str, set[frozenset[str]]] = {
        evaluator_id: set() for evaluator_id in own_item
    }
    for pair in pairs:
        workload[pair.evaluator_id] += 1
        judged[pair.evaluator_id].add(pair.key)

    while True:
        busiest = max(workload, key=lambda evaluator_id: workload[evaluator_id])
        idlest = min(workload, key=lambda evaluator_id: workload[evaluator_id])
        if workload[busiest] - workload[idlest] <= 1:
            return pairs

        chain = _find_chain(pairs, workload, judged, own_item, busiest)
        if chain is None:
            # No legal rearrangement left; this is as even as the classroom's
            # shape permits. check_invariants() is what decides whether that
            # is acceptable, so a genuinely impossible shape fails loudly
            # rather than shipping a lopsided workload.
            return pairs

        for index, taker in chain:
            giver = pairs[index].evaluator_id
            key = pairs[index].key
            pairs[index] = replace(pairs[index], evaluator_id=taker)
            judged[giver].discard(key)
            judged[taker].add(key)
            workload[giver] -= 1
            workload[taker] += 1


def _find_chain(
    pairs: Sequence[PairAssignment],
    workload: Mapping[str, int],
    judged: Mapping[str, set[frozenset[str]]],
    own_item: Mapping[str, str],
    start: str,
) -> list[tuple[int, str]] | None:
    """Breadth-first search for a legal chain of handovers away from ``start``.

    Returns the hops as ``(assignment index, new evaluator)`` in the order they
    should be applied, or ``None`` when no chain reaches an evaluator light
    enough to make the transfer worthwhile.
    """
    target_load = workload[start] - 2
    owned: dict[str, list[int]] = {}
    for index, pair in enumerate(pairs):
        owned.setdefault(pair.evaluator_id, []).append(index)

    # taker -> (giver, assignment index handed over)
    came_from: dict[str, tuple[str, int]] = {}
    visited = {start}
    queue: deque[str] = deque([start])

    while queue:
        giver = queue.popleft()
        for index in owned.get(giver, ()):
            key = pairs[index].key
            for taker in own_item:
                if taker in visited:
                    continue
                if own_item[taker] in key:  # would break INV-1
                    continue
                if key in judged[taker]:  # would break INV-2
                    continue

                came_from[taker] = (giver, index)
                if workload[taker] <= target_load:
                    return _unwind(came_from, taker)
                visited.add(taker)
                queue.append(taker)

    return None


def _unwind(
    came_from: Mapping[str, tuple[str, int]], end: str
) -> list[tuple[int, str]]:
    """Walk the BFS parents back to the start, then apply from the start out."""
    hops: list[tuple[int, str]] = []
    taker = end
    while taker in came_from:
        giver, index = came_from[taker]
        hops.append((index, taker))
        taker = giver
    hops.reverse()
    return hops
