"""Repository boundary the publish service depends on.

A Protocol (structural typing) instead of an ABC so the unit tests can hand
the service a FakeAssignmentRepo without inheriting from anything.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.roster import PairAssignment, RosterRow


class AssignmentRepo(Protocol):
    def get_roster(self, assignment_id: str) -> list[RosterRow]: ...

    def get_preview_count(self, assignment_id: str) -> int: ...

    def save_pair_assignments(
        self, assignment_id: str, assignments: list[PairAssignment]
    ) -> None: ...
