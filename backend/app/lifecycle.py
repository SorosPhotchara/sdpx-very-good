"""The assignment state machine of PRD §7.3.

Only the states an instructor drives are stored. OPEN and CLOSED are not: they
follow from the section deadlines, and storing them would need a scheduler and
would drift from the deadlines whenever one is moved. `phase` derives the view
callers want to show.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from . import models

DRAFT = "DRAFT"
PUBLISHED = "PUBLISHED"
FINALIZED = "FINALIZED"
ARCHIVED = "ARCHIVED"

# §7.3. Reopening a finalized assignment is allowed but needs a reason, which
# `move` enforces through REASON_REQUIRED.
TRANSITIONS: dict[str, set[str]] = {
    DRAFT: {PUBLISHED},
    PUBLISHED: {DRAFT, FINALIZED, ARCHIVED},
    FINALIZED: {PUBLISHED, ARCHIVED},
    ARCHIVED: set(),
}

# Actions that discard or overturn collected work, so the instructor has to say
# why on the record (§7.3, FR-SCORE-08's reasoning applied to the lifecycle).
REASON_REQUIRED = {"unpublish", "reopen"}


@dataclass(frozen=True)
class Phase:
    """The state to show a caller, including the part derived from deadlines."""

    status: str
    group_open: bool
    individual_open: bool

    @property
    def closed(self) -> bool:
        return self.status == PUBLISHED and not (self.group_open or self.individual_open)


def phase(assignment: models.Assignment, now: datetime | None = None) -> Phase:
    moment = now or datetime.now(UTC)

    def still_open(deadline: datetime | None) -> bool:
        if deadline is None:
            return False
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)
        return moment < deadline

    live = assignment.status == PUBLISHED
    return Phase(assignment.status,
                 live and still_open(assignment.group_deadline),
                 live and still_open(assignment.individual_deadline))


def is_final(assignment: models.Assignment, is_group: bool,
             now: datetime | None = None) -> bool:
    """Whether a section's scores are settled.

    Finalizing settles both sections at once; otherwise a section is settled
    when its own deadline has passed.
    """
    if assignment.status == FINALIZED:
        return True
    if assignment.status != PUBLISHED:
        return False
    deadline = assignment.group_deadline if is_group else assignment.individual_deadline
    if deadline is None:
        # A section with no deadline is not part of this assignment, so there is
        # nothing to settle rather than something already settled.
        return False
    current = phase(assignment, now)
    return not (current.group_open if is_group else current.individual_open)


def record(db: Session, assignment: models.Assignment, action: str, actor: str,
           reason: str | None = None, snapshot: dict | None = None) -> models.AssignmentEvent:
    event = models.AssignmentEvent(
        assignment_id=assignment.id, action=action, actor_email=actor,
        reason=reason, occurred_at=datetime.now(UTC), snapshot=snapshot,
    )
    db.add(event)
    return event


def move(db: Session, assignment: models.Assignment, target: str, action: str,
         actor: str, reason: str | None = None,
         report: dict | None = None) -> models.AssignmentEvent:
    """Apply one transition, refusing the ones §7.3 does not allow.

    `report` is the computed report to settle, required when finalizing. It is
    passed in rather than computed here so that scoring depends on the lifecycle
    and not the other way round.
    """
    if target not in TRANSITIONS:
        raise ValueError(f"Unknown assignment state {target}")
    allowed = TRANSITIONS[assignment.status]
    if target not in allowed:
        raise ValueError(
            f"Cannot {action} an assignment in state {assignment.status}")
    if action in REASON_REQUIRED and not (reason or "").strip():
        raise ValueError(f"{action.capitalize()} requires a reason")

    snapshot = None
    if target == FINALIZED:
        if report is None:
            raise ValueError("Finalizing requires the report to settle")
        # Inputs and outputs together, so the result stays readable even if the
        # formula changes later (FR-SCORE-09, AR-01).
        snapshot = {
            "formula": {
                "score_floor": assignment.score_floor,
                "score_ceiling": assignment.score_ceiling,
                "completion_threshold": assignment.completion_threshold,
                "instructor_weight": assignment.instructor_weight,
                "target_coverage": assignment.target_coverage,
            },
            "report": report,
        }
        assignment.finalized_at = datetime.now(UTC)
    if target == PUBLISHED and assignment.status == FINALIZED:
        assignment.finalized_at = None

    assignment.status = target
    return record(db, assignment, action, actor, reason, snapshot)
