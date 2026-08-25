"""In-memory stand-in for comparison storage.

Satisfies :class:`app.repositories.ComparisonRepository`. Note that it returns
*everything* it holds, drafts included — filtering to SUBMITTED is the scoring
engine's job (DR-01), and a fake that pre-filtered would hide a bug there.
"""

from __future__ import annotations

from typing import Sequence

from app.domain import Comparison
from app.scoring import Participation


class FakeComparisonRepo:
    def __init__(
        self,
        comparisons: Sequence[Comparison] = (),
        participation: dict[str, Participation] | None = None,
    ) -> None:
        self._comparisons = list(comparisons)
        self._participation = participation or {}

    def add(self, comparison: Comparison) -> None:
        self._comparisons.append(comparison)

    def set_participation(self, evaluator_id: str, value: Participation) -> None:
        self._participation[evaluator_id] = value

    def submitted_for(self, assignment_id: str) -> Sequence[Comparison]:
        return tuple(self._comparisons)

    def participation_of(
        self, assignment_id: str, evaluator_id: str
    ) -> Participation:
        return self._participation.get(
            evaluator_id,
            Participation(
                submitted_group=0,
                assigned_group=0,
                submitted_individual=0,
                assigned_individual=0,
            ),
        )
