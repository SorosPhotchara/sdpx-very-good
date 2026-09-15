from __future__ import annotations

from app.domain.roster import PairAssignment, RosterRow


class FakeAssignmentRepo:
    """In-memory stand-in for AssignmentRepo, used instead of a real database."""

    def __init__(self) -> None:
        self._rosters: dict[str, list[RosterRow]] = {}
        self._preview_counts: dict[str, int] = {}
        self._saved_assignments: dict[str, list[PairAssignment]] = {}

    def seed_roster(self, assignment_id: str, rows: list[RosterRow]) -> None:
        self._rosters[assignment_id] = rows

    def seed_preview_count(self, assignment_id: str, count: int) -> None:
        self._preview_counts[assignment_id] = count

    def get_roster(self, assignment_id: str) -> list[RosterRow]:
        return self._rosters[assignment_id]

    def get_preview_count(self, assignment_id: str) -> int:
        return self._preview_counts[assignment_id]

    def save_pair_assignments(
        self, assignment_id: str, assignments: list[PairAssignment]
    ) -> None:
        self._saved_assignments[assignment_id] = assignments

    def saved_assignments(self, assignment_id: str) -> list[PairAssignment]:
        return self._saved_assignments[assignment_id]
