"""Application services — the layer the API routes call (PRD §7.3–§7.6).

The engines stay pure; this is where storage and policy meet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Sequence

from .domain import (
    AssignmentConfig,
    Comparison,
    Criterion,
    Feasibility,
    Flag,
    PairAssignment,
    Side,
    Student,
)
from .pairing import (
    IndividualPlan,
    generate_group_pairs,
    generate_individual_pairs,
    individual_plan,
    solve_group_feasibility,
)
from .repositories import ComparisonRepository, RosterRepository
from .scoring import (
    ComponentScore,
    Participation,
    ScoringError,
    compute_component,
    final_personal_score,
    participation_multiplier,
    validate_criteria_weights,
)


@dataclass(frozen=True)
class PublishResult:
    """What the instructor sees before pairs go live (FR-PAIR-04)."""

    pairs: tuple[PairAssignment, ...]
    feasibility: Feasibility
    individual_plans: dict[str, IndividualPlan] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class FinalScore:
    student_id: str
    group_component: Decimal
    individual_component: Decimal
    participation_ratio: Decimal
    multiplier: Decimal
    total: Decimal
    flags: tuple[Flag, ...]


class AssignmentService:
    def __init__(
        self,
        roster_repo: RosterRepository,
        comparison_repo: ComparisonRepository | None = None,
    ) -> None:
        self._roster = roster_repo
        self._comparisons = comparison_repo

    # -- publish ------------------------------------------------------------

    def feasibility(self, classroom_id: str, config: AssignmentConfig) -> Feasibility:
        """Dry-run the numbers so nothing is a surprise after publish."""
        return solve_group_feasibility(self._roster.group_sizes(classroom_id), config)

    def publish(
        self,
        classroom_id: str,
        assignment_id: str,
        criteria: Sequence[Criterion],
        config: AssignmentConfig,
    ) -> PublishResult:
        """Generate and freeze every pair for the assignment (FR-PAIR-01).

        Pairs are computed once, here, and stored — never re-rolled at request
        time, or two students would answer different questions about the same
        assignment.
        """
        validate_criteria_weights(criteria, Side.GROUP)
        validate_criteria_weights(criteria, Side.INDIVIDUAL)

        students = list(self._roster.list_students(classroom_id))
        if not students:
            raise ScoringError("classroom has no students")

        pairs: list[PairAssignment] = []
        warnings: list[str] = []

        feasibility = solve_group_feasibility(
            self._roster.group_sizes(classroom_id), config
        )
        if feasibility.reduced:
            warnings.append(feasibility.reason)

        for criterion in (c for c in criteria if c.side is Side.GROUP):
            pairs.extend(generate_group_pairs(students, criterion, config, assignment_id))

        individual_plans: dict[str, IndividualPlan] = {}
        individual_criteria = [c for c in criteria if c.side is Side.INDIVIDUAL]
        # FR-ASSIGN-07: individual_max_score == 0 switches that half off, and
        # no pairs are generated for it at all.
        if individual_criteria and config.individual_max_score > 0:
            for group_id in sorted(self._roster.group_sizes(classroom_id)):
                members = list(self._roster.members_of_group(classroom_id, group_id))
                plan = individual_plan(len(members), config)
                individual_plans[group_id] = plan

                if not plan.enabled or plan.low_confidence:
                    warnings.append(f"กลุ่ม {group_id}: {plan.note}")
                if not plan.enabled:
                    continue

                for criterion in individual_criteria:
                    pairs.extend(
                        generate_individual_pairs(
                            members, criterion, config, assignment_id
                        )
                    )

        return PublishResult(
            pairs=tuple(pairs),
            feasibility=feasibility,
            individual_plans=individual_plans,
            warnings=tuple(warnings),
        )

    # -- scoring ------------------------------------------------------------

    def score_item(
        self,
        assignment_id: str,
        item_id: str,
        side: Side,
        criteria: Sequence[Criterion],
        config: AssignmentConfig,
    ) -> ComponentScore:
        max_score = (
            config.group_max_score if side is Side.GROUP else config.individual_max_score
        )
        return compute_component(
            item_id, side, criteria, self._submitted(assignment_id), max_score, config
        )

    def final_score(
        self,
        assignment_id: str,
        student: Student,
        criteria: Sequence[Criterion],
        config: AssignmentConfig,
    ) -> FinalScore:
        """Combine both components with the participation multiplier (§9.4)."""
        group = self.score_item(
            assignment_id, student.group_id, Side.GROUP, criteria, config
        )
        individual = self.score_item(
            assignment_id, student.id, Side.INDIVIDUAL, criteria, config
        )

        participation = self._participation(assignment_id, student.id)
        multiplier = participation_multiplier(participation, config)

        return FinalScore(
            student_id=student.id,
            group_component=group.total,
            individual_component=individual.total,
            participation_ratio=participation.ratio,
            multiplier=multiplier,
            total=final_personal_score(group.total, individual.total, multiplier),
            flags=tuple(
                sorted(set(group.flags) | set(individual.flags), key=lambda f: f.value)
            ),
        )

    # -- internals ----------------------------------------------------------

    def _submitted(self, assignment_id: str) -> Sequence[Comparison]:
        if self._comparisons is None:
            raise ScoringError("this service was built without a comparison repository")
        return self._comparisons.submitted_for(assignment_id)

    def _participation(self, assignment_id: str, evaluator_id: str) -> Participation:
        if self._comparisons is None:
            raise ScoringError("this service was built without a comparison repository")
        return self._comparisons.participation_of(assignment_id, evaluator_id)
