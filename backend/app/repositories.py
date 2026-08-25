"""Storage boundaries for the engines.

Declared as ``Protocol`` so the test fakes are checked against the same shape
as the real adapters. A fake that has quietly drifted from the interface
produces green tests and a broken deploy — which is the failure mode this file
exists to prevent.
"""

from __future__ import annotations

from typing import Mapping, Protocol, Sequence, runtime_checkable

from .domain import Comparison, Student
from .scoring import Participation


@runtime_checkable
class RosterRepository(Protocol):
    def list_students(self, classroom_id: str) -> Sequence[Student]: ...

    def group_sizes(self, classroom_id: str) -> Mapping[str, int]: ...

    def members_of_group(
        self, classroom_id: str, group_id: str
    ) -> Sequence[Student]: ...


@runtime_checkable
class ComparisonRepository(Protocol):
    def submitted_for(self, assignment_id: str) -> Sequence[Comparison]: ...

    def participation_of(
        self, assignment_id: str, evaluator_id: str
    ) -> Participation: ...
