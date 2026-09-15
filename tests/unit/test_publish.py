from __future__ import annotations

from app.domain.roster import allocate_pairs
from app.services.publish import publish
from factories import make_roster
from fakes.fake_assignment_repo import FakeAssignmentRepo


def test_publish_generates_exactly_the_previewed_number_of_pairs() -> None:
    roster = make_roster([3, 3, 2])
    repo = FakeAssignmentRepo()
    repo.seed_roster("assignment-1", roster)
    repo.seed_preview_count("assignment-1", len(allocate_pairs(roster)))

    published = publish("assignment-1", repo)

    assert len(published) == repo.get_preview_count("assignment-1")
    assert repo.saved_assignments("assignment-1") == published
