import unittest

from app.scoring import CHOICES, POINTS, PairVote, participation_multiplier, score_items


def votes_for(quality: float) -> list[PairVote]:
    """Two opposed answers whose weighted mean gives item 1 exactly `quality`.

    `quality` is the index q of PRD §9.2, so this lets a test state the q it
    means instead of reverse-engineering answers that happen to average to it.
    """
    return [PairVote(1, 2, choice=1, weight=quality),
            PairVote(1, 2, choice=CHOICES, weight=1 - quality)]


class ScoringTests(unittest.TestCase):
    def test_scale_is_six_point_forced_choice(self) -> None:
        # D1: six options, no tie, and option i mirrors option 7-i.
        self.assertEqual(CHOICES, 6)
        self.assertEqual(POINTS, ((1.0, 0.0), (0.8, 0.2), (0.6, 0.4),
                                  (0.4, 0.6), (0.2, 0.8), (0.0, 1.0)))
        for left, right in POINTS:
            self.assertNotEqual(left, right)
        for index, (left, right) in enumerate(POINTS):
            self.assertEqual((right, left), POINTS[CHOICES - 1 - index])

    def test_central_options_lean_because_there_is_no_tie(self) -> None:
        # The old 5-point scale split a mid answer 0.5/0.5. Forced choice has no
        # such answer: choice 3 is "left slightly better" and must favour left.
        result = score_items([1, 2], [PairVote(1, 2, choice=3)], 20, 0.5)
        # q 0.6 and 0.4 band-map to 0.84 and 0.76 of the 10-point share.
        self.assertAlmostEqual(result[1].weighted_score, 8.4)
        self.assertAlmostEqual(result[2].weighted_score, 7.6)
        self.assertGreater(result[1].weighted_score, result[2].weighted_score)

    def test_instructor_weight_changes_effective_vote_and_score(self) -> None:
        votes = [PairVote(1, 2, choice=1), PairVote(1, 2, choice=6, weight=3)]
        result = score_items([1, 2], votes, 100, 1)
        self.assertEqual(result[1].effective_votes, 4)
        # q 0.25 and 0.75 band-map to 70% and 90% of the maximum.
        self.assertAlmostEqual(result[1].weighted_score, 70)
        self.assertAlmostEqual(result[2].weighted_score, 90)

    def test_missing_votes_are_unscored_until_final(self) -> None:
        interim = score_items([1, 2, 3], [PairVote(1, 2, choice=1)], 10, 1)
        final = score_items([1, 2, 3], [PairVote(1, 2, choice=1)], 10, 1, final=True)
        self.assertIsNone(interim[3].weighted_score)
        self.assertEqual(final[3].weighted_score, 0)

    def test_invalid_vote_is_rejected(self) -> None:
        for choice in (0, 7):
            with self.assertRaisesRegex(ValueError, "choice and weight"):
                score_items([1, 2], [PairVote(1, 2, choice=choice)], 10, 1)

    def test_display_order_decides_which_subject_is_credited(self) -> None:
        # The stored choice is relative to what the evaluator saw (FR-PAIR-08),
        # so the same answer credits opposite subjects once the pair is flipped.
        shown_as_stored = score_items([1, 2], [PairVote(1, 2, choice=1)], 10, 1)
        shown_flipped = score_items([1, 2], [PairVote(2, 1, choice=1)], 10, 1)
        # The winner reaches the ceiling and the loser the floor, never zero:
        # zero is reserved for having no comparisons at all.
        self.assertAlmostEqual(shown_as_stored[1].weighted_score, 10)
        self.assertAlmostEqual(shown_as_stored[2].weighted_score, 6)
        self.assertAlmostEqual(shown_flipped[2].weighted_score, 10)
        self.assertAlmostEqual(shown_flipped[1].weighted_score, 6)

    def test_score_does_not_depend_on_how_many_items_are_compared(self) -> None:
        # D2: normalising to sum 1 gave each item its share of the cohort, so a
        # group's mark shrank as the class grew. Band mapping is per item, so the
        # same quality earns the same mark whatever the cohort size.
        two = score_items([1, 2], votes_for(0.75), 10, 1)
        many = score_items([1, 2, 3, 4, 5, 6], votes_for(0.75), 10, 1)
        self.assertAlmostEqual(two[1].score_ratio, 0.9)
        self.assertAlmostEqual(two[1].weighted_score, 9)
        self.assertAlmostEqual(many[1].weighted_score, two[1].weighted_score)

    def test_band_bounds_are_configurable_and_validated(self) -> None:
        strict = score_items([1, 2], votes_for(0.5), 10, 1, floor=0.0, ceiling=1.0)
        self.assertAlmostEqual(strict[1].weighted_score, 5)
        for floor, ceiling in ((0.6, 0.6), (0.9, 0.5), (-0.1, 1.0), (0.6, 1.1)):
            with self.assertRaisesRegex(ValueError, "Score band"):
                score_items([1, 2], votes_for(0.5), 10, 1, floor=floor, ceiling=ceiling)

    def test_prd_worked_example_group_scores(self) -> None:
        # PRD §9.5, group side: maximum 15, band 0.60-1.00, three criteria.
        rows = ((0.72, 40, 0.888, 5.328), (0.55, 35, 0.820, 4.305),
                (0.61, 25, 0.844, 3.165))
        total = 0.0
        for quality, weight_pct, ratio, expected in rows:
            scores = score_items([1, 2], votes_for(quality), 15, weight_pct / 100)
            self.assertAlmostEqual(scores[1].average_points, quality)
            self.assertAlmostEqual(scores[1].score_ratio, ratio)
            self.assertAlmostEqual(scores[1].weighted_score, expected)
            total += scores[1].weighted_score
        self.assertAlmostEqual(total, 12.798)

    def test_prd_worked_example_individual_scores(self) -> None:
        # PRD §9.5, individual side: maximum 5, two criteria at 50% each.
        rows = ((0.68, 0.872, 2.180), (0.45, 0.780, 1.950))
        total = 0.0
        for quality, ratio, expected in rows:
            scores = score_items([1, 2], votes_for(quality), 5, 0.5)
            self.assertAlmostEqual(scores[1].score_ratio, ratio)
            self.assertAlmostEqual(scores[1].weighted_score, expected)
            total += scores[1].weighted_score
        self.assertAlmostEqual(total, 4.130)

    def test_participation_multiplier_edges(self) -> None:
        self.assertEqual(participation_multiplier(0, 10), 0.0)
        self.assertEqual(participation_multiplier(9, 10), 1.0)    # threshold reached
        self.assertEqual(participation_multiplier(10, 10), 1.0)   # capped, no bonus
        self.assertEqual(participation_multiplier(0, 0), 1.0)     # nothing assigned
        self.assertAlmostEqual(participation_multiplier(45, 100), 0.5)
        for threshold in (0, -0.1, 1.1):
            with self.assertRaisesRegex(ValueError, "Completion threshold"):
                participation_multiplier(1, 2, threshold)

    def test_prd_worked_example_participation(self) -> None:
        # PRD §9.5: both students are in group Aurora, which earned 12.798. นก
        # submitted all 15 assigned comparisons, ต้น only 9 of them.
        group_work, nok_individual, ton_individual = 12.798, 4.130, 3.660

        nok = participation_multiplier(15, 15)
        self.assertAlmostEqual(nok, 1.0)
        self.assertAlmostEqual((group_work + nok_individual) * nok, 16.928)

        ton = participation_multiplier(9, 15)
        self.assertAlmostEqual(ton, 2 / 3)
        self.assertAlmostEqual((group_work + ton_individual) * ton, 10.972)

        # D5: ต้น not evaluating cost ต้น, not the group or their teammates.
        self.assertAlmostEqual(group_work, 12.798)
