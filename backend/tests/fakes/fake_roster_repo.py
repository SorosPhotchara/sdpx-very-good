"""In-memory stand-in for the roster storage.

It satisfies :class:`app.repositories.RosterRepository`; ``test_fakes.py``
asserts that at runtime, so this file cannot drift away from the real adapter
without a test going red.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from app.domain import Student


class FakeRosterRepo:
    def __init__(self, students: Sequence[Student] = ()) -> None:
        self._students: dict[str, list[Student]] = {}
        for student in students:
            self._students.setdefault("classroom-1", []).append(student)

    def add(self, classroom_id: str, student: Student) -> None:
        self._students.setdefault(classroom_id, []).append(student)

    def list_students(self, classroom_id: str) -> Sequence[Student]:
        return tuple(self._students.get(classroom_id, ()))

    def group_sizes(self, classroom_id: str) -> Mapping[str, int]:
        sizes: dict[str, int] = {}
        for student in self._students.get(classroom_id, ()):
            sizes[student.group_id] = sizes.get(student.group_id, 0) + 1
        return sizes

    def members_of_group(
        self, classroom_id: str, group_id: str
    ) -> Sequence[Student]:
        return tuple(
            student
            for student in self._students.get(classroom_id, ())
            if student.group_id == group_id
        )
