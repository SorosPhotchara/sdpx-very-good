from __future__ import annotations

from app.domain.roster import PairAssignment, allocate_pairs
from app.repositories.protocols import AssignmentRepo


def publish(assignment_id: str, repo: AssignmentRepo) -> list[PairAssignment]:
    """Re-run the pairing algorithm against the current roster and persist it.

    Recomputing from the roster at publish time (rather than trusting the
    count shown on the preview screen) is what US-PUBLISH-01 AC1 checks:
    the roster must not have drifted between preview and publish.
    """
    roster = repo.get_roster(assignment_id)
    assignments = allocate_pairs(roster)
    repo.save_pair_assignments(assignment_id, assignments)
    return assignments
