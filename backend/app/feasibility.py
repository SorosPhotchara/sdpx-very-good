"""Decide the coverage and workload a classroom can actually sustain.

Coverage (how many evaluators see each pair) and workload (how many pairs each
evaluator gets) are two views of the same total, so fixing both independently is
usually impossible. PRD §8.2 and §8.3 therefore derive one from the other and
report the numbers, rather than silently settling for whatever comes out.
"""

from dataclasses import dataclass
from math import ceil
from typing import Sequence

DEFAULT_TARGET_COVERAGE = 5
DEFAULT_GROUP_MAX_WORKLOAD = 8
# C(7,2): the most pairs a member of the largest supported group (A2: 3-8) can
# be asked to compare, so the ceiling never binds inside the supported range and
# complete enumeration (D4) survives. See FR-PAIR-14.
DEFAULT_INDIVIDUAL_MAX_WORKLOAD = 21


@dataclass(frozen=True)
class Feasibility:
    """What a side of an assignment can achieve, and why it fell short."""

    coverage: int          # evaluators per pair the system will aim for
    workload: int          # pairs per evaluator per criterion
    pairs: int             # distinct unordered pairs on this side
    comparisons: int       # coverage * pairs, the answers this side will ask for
    requested: int         # coverage asked for before any reduction
    reason: str = ""       # set only when coverage had to be reduced

    @property
    def reduced(self) -> bool:
        return self.coverage < self.requested

    @property
    def feasible(self) -> bool:
        return self.coverage > 0


def solve_group_feasibility(
    group_sizes: Sequence[int],
    target_coverage: int = DEFAULT_TARGET_COVERAGE,
    max_workload: int = DEFAULT_GROUP_MAX_WORKLOAD,
) -> Feasibility:
    """Coverage and workload for group evaluation, per PRD §8.2.

    Reduces the target until all three constraints hold, and explains the
    reduction with the numbers that forced it (FR-PAIR-05).
    """
    sizes = [size for size in group_sizes if size > 0]
    groups = len(sizes)
    students = sum(sizes)
    if groups < 3:
        return Feasibility(0, 0, 0, 0, target_coverage,
                           f"ต้องมีอย่างน้อย 3 กลุ่มที่มีสมาชิก แต่ห้องนี้มี {groups} กลุ่ม")
    if target_coverage < 1 or max_workload < 1:
        raise ValueError("Target coverage and max workload must be positive")

    pairs = groups * (groups - 1) // 2
    # Nobody may judge a pair containing their own group, so the pair of the two
    # largest groups has the fewest eligible evaluators. That is constraint (3).
    largest_two = sum(sorted(sizes, reverse=True)[:2])
    eligible_floor = students - largest_two
    # Constraint (1): an evaluator cannot be given more pairs than exist without
    # their own group in them.
    workload_ceiling = min(max_workload, pairs - (groups - 1))

    for coverage in range(min(target_coverage, eligible_floor), 0, -1):
        workload = ceil(pairs * coverage / students)
        if workload <= workload_ceiling:
            reason = ""
            if coverage < target_coverage:
                reason = (
                    f"ห้องนี้มี {groups} กลุ่ม ({students} คน) แต่ละคู่มีผู้มีสิทธิ์ประเมิน "
                    f"อย่างน้อย {eligible_floor} คน และประเมินได้ไม่เกิน {workload_ceiling} คู่ต่อคน "
                    f"จึงตั้ง coverage ได้สูงสุด {coverage} ครั้งต่อคู่ "
                    f"(ไม่ใช่ {target_coverage} ตามค่าตั้งต้น) "
                    f"นักศึกษาแต่ละคนจะได้ {workload} คู่ต่อเกณฑ์"
                )
            return Feasibility(coverage, workload, pairs, pairs * coverage,
                               target_coverage, reason)

    return Feasibility(0, 0, pairs, 0, target_coverage,
                       f"ไม่สามารถจัดคู่ได้: {pairs} คู่ต่อ {students} คน "
                       f"ต้องการงานเกิน {workload_ceiling} คู่ต่อคน แม้ที่ coverage 1")


def solve_individual_feasibility(
    member_count: int,
    max_workload: int = DEFAULT_INDIVIDUAL_MAX_WORKLOAD,
) -> Feasibility:
    """Coverage and workload for individual evaluation, per PRD §8.3.

    Within a group this is complete enumeration (D4): every member compares every
    pair that does not contain them, which gives coverage `m - 2` exactly. Only a
    group larger than the supported range can breach the workload ceiling, and
    FR-PAIR-14 then trades coverage away rather than the ceiling.
    """
    if max_workload < 1:
        raise ValueError("Max workload must be positive")
    if member_count < 3:
        return Feasibility(0, 0, 0, 0, max(member_count - 2, 0),
                           f"กลุ่มมีสมาชิก {member_count} คน ต้องมีอย่างน้อย 3 คน "
                           f"จึงจะมีผู้ประเมินที่ไม่ใช่คู่ที่ถูกประเมิน")

    pairs = member_count * (member_count - 1) // 2
    full_coverage = member_count - 2
    per_evaluator = (member_count - 1) * (member_count - 2) // 2

    if per_evaluator <= max_workload:
        return Feasibility(full_coverage, per_evaluator, pairs,
                           pairs * full_coverage, full_coverage)

    # FR-PAIR-14: hold the ceiling and report the coverage it costs.
    coverage = max(1, member_count * max_workload // pairs)
    reason = (
        f"กลุ่มมีสมาชิก {member_count} คน ครบทุกคู่คือ {per_evaluator} คู่ต่อคนต่อเกณฑ์ "
        f"ซึ่งเกินเพดาน {max_workload} คู่ จึงลด coverage จาก {full_coverage} "
        f"เหลือ {coverage} ครั้งต่อคู่"
    )
    return Feasibility(coverage, max_workload, pairs, pairs * coverage,
                       full_coverage, reason)
