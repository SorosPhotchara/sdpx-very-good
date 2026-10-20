"""Coverage and workload feasibility, against the worked examples in the PRD."""

import unittest

from app.feasibility import solve_group_feasibility, solve_individual_feasibility


class GroupFeasibilityTests(unittest.TestCase):
    def test_prd_example_one_large_classroom_meets_the_target(self) -> None:
        # §8.2 example 1: S=200, N=10 groups of 20, R=5.
        plan = solve_group_feasibility([20] * 10, target_coverage=5, max_workload=8)
        self.assertEqual(plan.pairs, 45)            # C(10,2)
        self.assertEqual(plan.coverage, 5)
        self.assertEqual(plan.workload, 2)          # ceil(45*5/200)
        self.assertEqual(plan.comparisons, 225)
        self.assertFalse(plan.reduced)
        self.assertEqual(plan.reason, "")

    def test_prd_example_two_small_classroom_reduces_the_target(self) -> None:
        # §8.2 example 2: S=12, N=3 groups of 4. R=5 is impossible because an
        # evaluator may judge only the one pair without their own group in it.
        plan = solve_group_feasibility([4, 4, 4], target_coverage=5, max_workload=8)
        self.assertEqual(plan.pairs, 3)
        self.assertEqual(plan.coverage, 4)          # not 5
        self.assertEqual(plan.workload, 1)
        self.assertTrue(plan.reduced)
        # FR-PAIR-05: the reduction is explained with the numbers behind it.
        for fragment in ("3 กลุ่ม", "12 คน", "4 ครั้งต่อคู่", "1 คู่ต่อเกณฑ์"):
            self.assertIn(fragment, plan.reason)

    def test_fewer_than_three_groups_is_not_feasible(self) -> None:
        for sizes in ([], [5], [5, 5], [5, 5, 0]):
            plan = solve_group_feasibility(sizes)
            self.assertFalse(plan.feasible)
            self.assertEqual(plan.coverage, 0)
            self.assertIn("3 กลุ่ม", plan.reason)

    def test_workload_ceiling_reduces_coverage(self) -> None:
        # Many groups and few students: the per-student ceiling binds first.
        generous = solve_group_feasibility([1] * 12, target_coverage=5, max_workload=30)
        tight = solve_group_feasibility([1] * 12, target_coverage=5, max_workload=3)
        self.assertLessEqual(tight.workload, 3)
        self.assertLess(tight.coverage, generous.coverage)
        self.assertTrue(tight.reduced)

    def test_coverage_never_exceeds_the_eligible_pool(self) -> None:
        # Two big groups and one small one: the pair of the two big groups has
        # only the small group left to judge it, which caps coverage (§8.2 (3)).
        plan = solve_group_feasibility([10, 10, 2], target_coverage=5, max_workload=8)
        self.assertLessEqual(plan.coverage, 2)
        self.assertTrue(plan.reduced)

    def test_invalid_inputs_are_rejected(self) -> None:
        for coverage, workload in ((0, 8), (5, 0), (-1, 8)):
            with self.assertRaises(ValueError):
                solve_group_feasibility([4, 4, 4], coverage, workload)


class IndividualFeasibilityTests(unittest.TestCase):
    def test_matches_the_prd_group_size_table(self) -> None:
        # §8.3: coverage is m-2 and workload C(m-1,2) for every supported size,
        # because the default ceiling (21) does not bind within A2's 3-8 range.
        expected = {
            2: (0, 0, 0),      # no individual evaluation at all
            3: (1, 1, 3),
            4: (2, 3, 6),
            5: (3, 6, 10),
            6: (4, 10, 15),
            7: (5, 15, 21),
            8: (6, 21, 28),
        }
        for members, (coverage, workload, pairs) in expected.items():
            plan = solve_individual_feasibility(members)
            with self.subTest(members=members):
                self.assertEqual((plan.coverage, plan.workload, plan.pairs),
                                 (coverage, workload, pairs))
                self.assertFalse(plan.reduced)
                if members >= 3:
                    # The §8.3 consistency identity.
                    self.assertEqual(members * workload, pairs * coverage)

    def test_groups_below_three_get_no_individual_evaluation(self) -> None:
        for members in (0, 1, 2):
            plan = solve_individual_feasibility(members)
            self.assertFalse(plan.feasible)
            self.assertIn("อย่างน้อย 3 คน", plan.reason)

    def test_a_shared_ceiling_of_eight_would_contradict_the_coverage_table(self) -> None:
        # The reason the ceilings are split per side (FR-PAIR-14): at 8, coverage
        # would fall as groups grow, which contradicts D4 and the §8.3 table.
        coverages = {members: solve_individual_feasibility(members, max_workload=8).coverage
                     for members in (5, 6, 7, 8)}
        self.assertEqual(coverages[5], 3)
        self.assertLess(coverages[8], coverages[5])
        # With the real default the table holds instead.
        self.assertEqual(solve_individual_feasibility(8).coverage, 6)

    def test_oversized_group_trades_coverage_for_the_ceiling(self) -> None:
        # Outside the supported range FR-PAIR-14 finally applies.
        plan = solve_individual_feasibility(9)
        self.assertEqual(plan.workload, 21)       # the ceiling holds
        self.assertLess(plan.coverage, 7)         # m - 2 was not affordable
        self.assertTrue(plan.reduced)
        for fragment in ("9 คน", "เกินเพดาน 21 คู่"):
            self.assertIn(fragment, plan.reason)

    def test_invalid_ceiling_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            solve_individual_feasibility(5, max_workload=0)


if __name__ == "__main__":
    unittest.main()
