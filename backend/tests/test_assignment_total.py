import unittest
from math import inf, nan

from pydantic import ValidationError

from app.schemas import AssignmentSetup


class AssignmentTotalTests(unittest.TestCase):
    def test_total_is_derived_and_rejects_a_mismatch(self) -> None:
        fields = dict(group_score=10, individual_score=4,
                      group_participation_max=2, individual_participation_max=1)
        self.assertEqual(AssignmentSetup(title="Review", **fields).total_score, 17)
        self.assertEqual(AssignmentSetup(title="Review", total_score=17, **fields).total_score, 17)
        with self.assertRaises(ValidationError):
            AssignmentSetup(title="Review", total_score=18, **fields)

    def test_score_maxima_must_be_finite_and_nonnegative(self) -> None:
        for invalid in (-1, inf, nan):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                AssignmentSetup(title="Review", group_score=invalid)

    def test_instructor_weight_must_be_finite_and_positive(self) -> None:
        for invalid in (0, -1, inf, nan):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                AssignmentSetup(title="Review", instructor_weight=invalid)
