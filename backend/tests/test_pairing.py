import unittest
from collections import Counter

from app.pairing import allocate_group_pairs, allocate_individual_pairs


class PairingTests(unittest.TestCase):
    def test_group_pairs_use_distinct_eligible_evaluators_without_self_evaluation(self) -> None:
        groups = {10: [1, 2], 20: [3, 4], 30: [5, 6]}
        allocations = allocate_group_pairs(groups, seed=7)

        self.assertEqual(
            Counter((item.left_id, item.right_id) for item in allocations),
            {(10, 20): 2, (10, 30): 2, (20, 30): 2},
        )
        self.assertEqual(len(allocations), len({
            (item.left_id, item.right_id, item.evaluator_id) for item in allocations
        }))
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
        self.assertEqual(len(allocations), 3)
        self.assertTrue(all(
            item.evaluator_id not in (item.left_id, item.right_id)
            for item in allocations
        ))
        self.assertEqual(len(allocations), len({
            (item.left_id, item.right_id, item.evaluator_id) for item in allocations
        }))
        self.assertEqual(allocate_individual_pairs([1, 2]), [])

    def test_coverage_caps_at_five_distinct_eligible_evaluators(self) -> None:
        members = list(range(1, 9))
        allocations = allocate_individual_pairs(members, seed=11)
        coverage = Counter((item.left_id, item.right_id) for item in allocations)

        self.assertEqual(len(coverage), 28)
        self.assertEqual(set(coverage.values()), {5})
        self.assertEqual(len(allocations), len({
            (item.left_id, item.right_id, item.evaluator_id) for item in allocations
        }))
        self.assertEqual(allocations, allocate_individual_pairs(members, seed=11))

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

    def test_every_eligible_evaluator_is_used_when_students_outnumber_slots(self) -> None:
        groups = {10: list(range(1, 11)), 20: list(range(11, 21)), 30: list(range(21, 31))}
        allocations = allocate_group_pairs(groups, seed=5)
        loads = Counter(item.evaluator_id for item in allocations)
        coverage = Counter((item.left_id, item.right_id) for item in allocations)

        self.assertEqual(len(allocations), 30)
        self.assertEqual(sorted(loads), list(range(1, 31)))
        self.assertEqual(set(loads.values()), {1})
        self.assertEqual(set(coverage.values()), {10})
        self.assertEqual(len(allocations), len({
            (item.left_id, item.right_id, item.evaluator_id) for item in allocations
        }))
        self.assertEqual(allocations, allocate_group_pairs(groups, seed=5))

    def test_each_criterion_covers_every_evaluator_while_totals_stay_balanced(self) -> None:
        groups = {10: list(range(1, 11)), 20: list(range(11, 21)), 30: list(range(21, 31))}
        cumulative: Counter[int] = Counter()

        for seed in (10, 11, 12):
            allocations = allocate_group_pairs(groups, seed=seed, initial_loads=cumulative)
            self.assertEqual(set(Counter(item.evaluator_id for item in allocations).values()), {1})
            cumulative.update(item.evaluator_id for item in allocations)

        self.assertEqual(set(cumulative.values()), {3})

    def test_individual_floor_overrides_cumulative_imbalance(self) -> None:
        members = list(range(1, 9))
        allocations = allocate_individual_pairs(members, seed=13, initial_loads={1: 1000})
        loads = Counter(item.evaluator_id for item in allocations)

        self.assertEqual(len(allocations), 141)
        self.assertEqual(loads[1], 1)
        self.assertEqual(len(loads), 8)
        self.assertEqual(len(allocations), len({
            (item.left_id, item.right_id, item.evaluator_id) for item in allocations
        }))
        self.assertEqual(Counter(item.evaluator_id for item in allocate_individual_pairs(
            members, seed=13, initial_loads={1: 1000}, minimum=0,
        ))[1], 0)
