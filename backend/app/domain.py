"""Domain types for the pairing and scoring engines (PRD §11).

Kept separate from ``app.models`` (the SQLAlchemy tables) on purpose: the
engines must stay pure functions over plain data (AR-01) so a recompute on the
same rows produces the same digits every time (FR-SCORE-10).

Scores are ``Decimal``, never ``float`` — a grade document that disagrees with
itself in the third decimal place is a support ticket, not a rounding detail
(DR-04).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class Side(str, Enum):
    """Which half of an assignment a criterion or pair belongs to."""

    GROUP = "GROUP"
    INDIVIDUAL = "INDIVIDUAL"


class ComparisonStatus(str, Enum):
    """PRD §11.1 ``comparison.status``. Only SUBMITTED is scored (DR-01)."""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    EXCLUDED = "EXCLUDED"


class Flag(str, Enum):
    """Flags attached to a computed score (PRD §10)."""

    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    OVERRIDDEN = "OVERRIDDEN"


@dataclass(frozen=True)
class Group:
    id: str
    name: str


@dataclass(frozen=True)
class Student:
    id: str
    email: str
    display_name: str
    group_id: str


@dataclass(frozen=True)
class Criterion:
    id: str
    side: Side
    name: str
    weight_pct: Decimal


@dataclass(frozen=True)
class AssignmentConfig:
    """The knobs an instructor can turn per assignment (PRD §11.1)."""

    group_max_score: Decimal = Decimal("15")
    individual_max_score: Decimal = Decimal("5")
    target_coverage: int = 5
    max_workload: int = 8
    min_comparisons: int = 3
    score_floor: Decimal = Decimal("0.600")
    score_ceiling: Decimal = Decimal("1.000")
    completion_threshold: Decimal = Decimal("0.900")
    instructor_weight: Decimal = Decimal("1.0")
    pairing_seed: int = 0

    def __post_init__(self) -> None:
        if self.score_floor >= self.score_ceiling:
            raise ValueError("score_floor must be strictly below score_ceiling")
        if self.target_coverage < 1:
            raise ValueError("target_coverage must be at least 1")
        if self.max_workload < 1:
            raise ValueError("max_workload must be at least 1")
        if self.instructor_weight < 0:
            raise ValueError("instructor_weight must not be negative")
        if self.completion_threshold <= 0:
            raise ValueError("completion_threshold must be positive")


@dataclass(frozen=True)
class PairAssignment:
    """One evaluator's job: compare ``item_a`` against ``item_b`` (PRD §11.1).

    ``display_left_item_id`` records which side each item was actually shown
    on, because the position is randomised (D8/FR-PAIR-08). Without it, the
    stored choice cannot be mapped back to an item at all.
    """

    criterion_id: str
    side: Side
    evaluator_id: str
    item_a_id: str
    item_b_id: str
    display_left_item_id: str

    def __post_init__(self) -> None:
        if self.item_a_id == self.item_b_id:
            raise ValueError("a pair must hold two distinct items")
        if self.display_left_item_id not in (self.item_a_id, self.item_b_id):
            raise ValueError("display_left_item_id must be one of the two items")

    @property
    def key(self) -> frozenset[str]:
        """The unordered pair, for coverage bookkeeping."""
        return frozenset((self.item_a_id, self.item_b_id))

    @property
    def display_right_item_id(self) -> str:
        return (
            self.item_b_id
            if self.display_left_item_id == self.item_a_id
            else self.item_a_id
        )


@dataclass(frozen=True)
class Comparison:
    """A submitted (or drafted) answer to one :class:`PairAssignment`."""

    pair: PairAssignment
    choice: int
    evaluator_weight: Decimal = Decimal("1.0")
    status: ComparisonStatus = ComparisonStatus.SUBMITTED

    def __post_init__(self) -> None:
        if not 1 <= self.choice <= 6:
            raise ValueError("choice must be on the 6-point scale (1..6)")
        if self.evaluator_weight < 0:
            raise ValueError("evaluator_weight must not be negative")


@dataclass
class Feasibility:
    """The answer to "can we actually run this?" (PRD §8.2, FR-PAIR-04/05)."""

    coverage: int
    workload: int
    total_comparisons: int
    reduced: bool
    reason: str
    possible_pairs: int = 0
    notes: list[str] = field(default_factory=list)


class PairingInfeasibleError(Exception):
    """Raised when no coverage ≥ 1 can satisfy the constraints in PRD §8.2."""
