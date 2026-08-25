"""Object mothers for the PairEval engines.

Every factory takes overrides, so a test names only the field it cares about
and the reader can tell at a glance which value is the point of the test.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.domain import (
    AssignmentConfig,
    Comparison,
    ComparisonStatus,
    Criterion,
    Group,
    PairAssignment,
    Side,
    Student,
)
from app.scoring import Participation


def make_group(**overrides: Any) -> Group:
    defaults = {"id": "g1", "name": "Aurora"}
    return Group(**{**defaults, **overrides})


def make_student(**overrides: Any) -> Student:
    defaults = {
        "id": "s1",
        "email": "student1@uni.ac.th",
        "display_name": "Student 1",
        "group_id": "g1",
    }
    return Student(**{**defaults, **overrides})


def make_criterion(**overrides: Any) -> Criterion:
    defaults = {
        "id": "c1",
        "side": Side.GROUP,
        "name": "User Experience",
        "weight_pct": Decimal("100"),
    }
    return Criterion(**{**defaults, **overrides})


def make_config(**overrides: Any) -> AssignmentConfig:
    return AssignmentConfig(**overrides)


def make_pair(**overrides: Any) -> PairAssignment:
    defaults = {
        "criterion_id": "c1",
        "side": Side.GROUP,
        "evaluator_id": "s99",
        "item_a_id": "g1",
        "item_b_id": "g2",
        "display_left_item_id": "g1",
    }
    return PairAssignment(**{**defaults, **overrides})


def make_comparison(**overrides: Any) -> Comparison:
    defaults = {
        "pair": make_pair(),
        "choice": 1,
        "evaluator_weight": Decimal("1.0"),
        "status": ComparisonStatus.SUBMITTED,
    }
    return Comparison(**{**defaults, **overrides})


def make_participation(**overrides: Any) -> Participation:
    defaults = {
        "submitted_group": 12,
        "assigned_group": 12,
        "submitted_individual": 3,
        "assigned_individual": 3,
    }
    return Participation(**{**defaults, **overrides})


def make_classroom(num_groups: int, group_size: int) -> list[Student]:
    """A classroom of ``num_groups × group_size`` students, evenly grouped."""
    students: list[Student] = []
    for group_index in range(num_groups):
        group_id = f"g{group_index + 1}"
        for member_index in range(group_size):
            student_id = f"s{group_index * group_size + member_index + 1}"
            students.append(
                make_student(
                    id=student_id,
                    email=f"{student_id}@uni.ac.th",
                    display_name=f"Student {student_id}",
                    group_id=group_id,
                )
            )
    return students
