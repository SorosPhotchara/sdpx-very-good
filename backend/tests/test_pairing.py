import unittest
from collections import Counter

from app.pairing import allocate_group_pairs, allocate_individual_pairs


class PairingTests(unittest.TestCase):
    def test_group_pairs_reach_coverage_without_self_evaluation(self) -> None:
        groups = {10: [1, 2], 20: [3, 4], 30: [5, 6]}
        allocations = allocate_group_pairs(groups, seed=7)

        self.assertEqual(
            Counter((item.left_id, item.right_id) for item in allocations),
            {(10, 20): 5, (10, 30): 5, (20, 30): 5},
        )
        self.assertTrue(all(
            item.evaluator_id not in groups[item.left_id]
            and item.evaluator_id not in groups[item.right_id]
            for item in allocations
        ))
        loads = Counter(item.evaluator_id for item in allocations)
        self.assertLessEqual(max(loads.values()) - min(loads.values()), 1)

    def test_less_than_three_nonempty_groups_cannot_be_published(self) -> None:
        with self.assertRaisesRegex(ValueError, "three non-empty groups"):
            allocate_group_pairs({10: [1], 20: [2], 30: []})

    def test_individual_pairs_only_use_other_group_members(self) -> None:
        allocations = allocate_individual_pairs([1, 2, 3], seed=3)
        self.assertEqual(len(allocations), 15)
        self.assertTrue(all(
            item.evaluator_id not in (item.left_id, item.right_id)
            for item in allocations
        ))
        self.assertEqual(allocate_individual_pairs([1, 2]), [])

    def test_target_classroom_size_covers_all_group_pairs(self) -> None:
        groups = {
            group_id: list(range(group_id * 20, group_id * 20 + 20))
            for group_id in range(10)
        }
        allocations = allocate_group_pairs(groups, seed=11)
        coverage = Counter((item.left_id, item.right_id) for item in allocations)

        self.assertEqual(len(allocations), 45 * 5)
        self.assertEqual(len(coverage), 45)
        self.assertEqual(set(coverage.values()), {5})
