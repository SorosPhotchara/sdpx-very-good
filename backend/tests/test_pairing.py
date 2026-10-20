import unittest
from collections import Counter
from itertools import combinations

from app.feasibility import solve_group_feasibility, solve_individual_feasibility
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

    def test_display_order_is_random_but_reproducible_from_the_seed(self) -> None:
        # FR-PAIR-08 / D8: each comparison gets a randomised left-right order,
        # and INV-5 still has to hold, so the same seed reproduces it exactly.
        members = list(range(1, 9))
        allocations = allocate_individual_pairs(members, seed=11)
        flips = [item.flipped for item in allocations]

        self.assertEqual(flips, [item.flipped for item in
                                 allocate_individual_pairs(members, seed=11)])
        self.assertEqual({type(flip) for flip in flips}, {bool})
        # Both orders must actually occur, or the randomisation is not happening.
        self.assertEqual(set(flips), {False, True})
        self.assertNotEqual(flips, [item.flipped for item in
                                    allocate_individual_pairs(members, seed=12)])

    def test_individual_coverage_is_complete_enumeration(self) -> None:
        # D4 / §8.3: inside a group of m, every member compares every pair that
        # does not contain them, so coverage is exactly m - 2 and the identity
        # m * C(m-1,2) == C(m,2) * (m-2) holds.
        members = list(range(1, 9))
        allocations = allocate_individual_pairs(members, seed=11)
        coverage = Counter((item.left_id, item.right_id) for item in allocations)
        loads = Counter(item.evaluator_id for item in allocations)

        self.assertEqual(len(coverage), 28)               # C(8,2)
        self.assertEqual(set(coverage.values()), {6})     # m - 2
        self.assertEqual(set(loads.values()), {21})       # C(7,2)
        self.assertEqual(len(allocations), 168)           # 28 * 6 == 8 * 21
        self.assertEqual(len(allocations), len({
            (item.left_id, item.right_id, item.evaluator_id) for item in allocations
        }))
        self.assertEqual(allocations, allocate_individual_pairs(members, seed=11))

    def test_individual_workload_ceiling_trades_coverage_not_workload(self) -> None:
        # FR-PAIR-14: when complete enumeration would exceed the ceiling, the
        # ceiling holds and coverage drops; nobody is given more than the cap.
        members = list(range(1, 9))
        allocations = allocate_individual_pairs(members, seed=11, coverage=2, max_workload=8)
        loads = Counter(item.evaluator_id for item in allocations)
        coverage = Counter((item.left_id, item.right_id) for item in allocations)

        self.assertLessEqual(max(loads.values()), 8)
        self.assertLessEqual(max(coverage.values()), 2)
        self.assertEqual(allocations, allocate_individual_pairs(
            members, seed=11, coverage=2, max_workload=8))

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

    def test_individual_enumeration_ignores_cumulative_imbalance(self) -> None:
        # Complete enumeration leaves no choice to balance: a member already
        # loaded from earlier criteria still owes every pair they can judge, so
        # the floor rule never has to rescue anyone on this side.
        members = list(range(1, 9))
        allocations = allocate_individual_pairs(members, seed=13, initial_loads={1: 1000})
        loads = Counter(item.evaluator_id for item in allocations)

        self.assertEqual(len(allocations), 168)
        self.assertEqual(set(loads.values()), {21})
        self.assertEqual(len(loads), 8)
        self.assertEqual(len(allocations), len({
            (item.left_id, item.right_id, item.evaluator_id) for item in allocations
        }))

    def test_floor_gives_work_when_there_are_fewer_slots_than_evaluators(self) -> None:
        # Three groups make three pairs, so a feasible coverage of 2 fills only
        # six slots among 22 students. Balancing cannot help - there is nothing
        # to redistribute - so the floor rule is the only thing that stops most
        # of the class from opening an empty page.
        groups = {10: list(range(1, 11)), 20: list(range(11, 21)), 30: [21, 22]}
        planned = allocate_group_pairs(groups, coverage=2, seed=13, minimum=0)
        self.assertEqual(len(planned), 6)
        self.assertEqual(len({item.evaluator_id for item in planned}), 6)

        with_floor = allocate_group_pairs(groups, coverage=2, seed=13)
        loads = Counter(item.evaluator_id for item in with_floor)
        self.assertEqual(len(loads), 22)
        self.assertEqual(set(loads.values()), {1})
        # The cost of that is coverage past the target on some pairs, which is
        # the documented exception to INV-3.
        coverage = Counter((item.left_id, item.right_id) for item in with_floor)
        self.assertGreater(max(coverage.values()), 2)


# Classroom shapes chosen to stress eligibility: lopsided groups, singleton
# groups, the smallest publishable room and the 200-student target.
CLASSROOM_SHAPES = (
    [4, 4, 4], [3, 3, 3], [2, 2, 2], [10, 10, 2], [8, 3, 3], [5, 5, 5, 5],
    [1, 1, 1], [1] * 6, [1] * 12, [6] * 5, [2, 3, 4, 5], [7] * 4,
    [3, 4, 5, 6, 7, 8], [20] * 5, [20] * 10, [9, 1, 1],
)


class PairingInvariantTests(unittest.TestCase):
    """NFR-MAINT-02: sweep §8.4's invariants over many shapes and seeds.

    A sweep rather than a generator library, so it adds no dependency and the
    failing case is always reproducible from the printed shape and seed.
    """

    def _groups(self, sizes):
        groups, next_id = {}, 1
        for index, size in enumerate(sizes, start=10):
            groups[index] = list(range(next_id, next_id + size))
            next_id += size
        return groups

    def test_group_invariants_hold_across_shapes_and_seeds(self) -> None:
        for sizes in CLASSROOM_SHAPES:
            plan = solve_group_feasibility(sizes)
            if not plan.feasible:
                continue
            groups = self._groups(sizes)
            member_group = {member: group for group, members in groups.items()
                            for member in members}
            for seed in (1, 2, 3, 4):
                with self.subTest(sizes=sizes, seed=seed):
                    kwargs = dict(coverage=plan.coverage, seed=seed, max_workload=8)
                    allocations = allocate_group_pairs(groups, **kwargs)
                    keys = [(item.left_id, item.right_id, item.evaluator_id)
                            for item in allocations]

                    # INV-1: never your own group.
                    for item in allocations:
                        self.assertNotIn(member_group[item.evaluator_id],
                                         (item.left_id, item.right_id))
                    # INV-2: never the same pair twice.
                    self.assertEqual(len(keys), len(set(keys)))
                    # INV-4: workloads within one of each other.
                    loads = Counter(item.evaluator_id for item in allocations)
                    counts = [loads.get(member, 0) for member in member_group]
                    self.assertLessEqual(max(counts) - min(counts), 1)
                    # INV-5: same seed, same result.
                    self.assertEqual(allocations, allocate_group_pairs(groups, **kwargs))
                    # Floor rule: nobody is left with nothing to open.
                    self.assertEqual(min(counts), max(1, min(counts)))
                    self.assertGreater(min(counts), 0)

                    # INV-3 applies to the planned allocation. The floor rule is
                    # the documented exception: handing work to an otherwise idle
                    # evaluator can push one pair past the target.
                    planned = allocate_group_pairs(groups, minimum=0, **kwargs)
                    coverage = Counter((item.left_id, item.right_id) for item in planned)
                    spread = [coverage.get(pair, 0)
                              for pair in combinations(sorted(groups), 2)]
                    self.assertLessEqual(max(spread) - min(spread), 1)

    def test_individual_invariants_hold_across_group_sizes(self) -> None:
        for members_count in range(3, 14):
            plan = solve_individual_feasibility(members_count)
            members = list(range(1, members_count + 1))
            for seed in (1, 2, 3):
                with self.subTest(members=members_count, seed=seed):
                    kwargs = dict(coverage=plan.coverage, seed=seed, max_workload=21)
                    allocations = allocate_individual_pairs(members, **kwargs)
                    keys = [(item.left_id, item.right_id, item.evaluator_id)
                            for item in allocations]

                    for item in allocations:               # INV-1
                        self.assertNotIn(item.evaluator_id, (item.left_id, item.right_id))
                    self.assertEqual(len(keys), len(set(keys)))              # INV-2
                    coverage = Counter((item.left_id, item.right_id) for item in allocations)
                    spread = [coverage.get(pair, 0) for pair in combinations(members, 2)]
                    self.assertLessEqual(max(spread) - min(spread), 1)       # INV-3
                    loads = Counter(item.evaluator_id for item in allocations)
                    counts = [loads.get(member, 0) for member in members]
                    self.assertLessEqual(max(counts) - min(counts), 1)       # INV-4
                    self.assertEqual(allocations,
                                     allocate_individual_pairs(members, **kwargs))  # INV-5
                    self.assertLessEqual(max(counts), 21)   # FR-PAIR-14 ceiling
