import unittest

from app.scoring import PairVote, score_items


class ScoringTests(unittest.TestCase):
    def test_tie_splits_relative_score_evenly(self) -> None:
        result = score_items([1, 2], [PairVote(1, 2, choice=3)], 20, 0.5)
        self.assertEqual(result[1].weighted_score, 5)
        self.assertEqual(result[2].weighted_score, 5)

    def test_instructor_weight_changes_effective_vote_and_score(self) -> None:
        votes = [PairVote(1, 2, choice=1), PairVote(1, 2, choice=5, weight=3)]
        result = score_items([1, 2], votes, 100, 1)
        self.assertEqual(result[1].effective_votes, 4)
        self.assertEqual(result[1].weighted_score, 25)
        self.assertEqual(result[2].weighted_score, 75)

    def test_missing_votes_are_unscored_until_final(self) -> None:
        interim = score_items([1, 2, 3], [PairVote(1, 2, choice=1)], 10, 1)
        final = score_items([1, 2, 3], [PairVote(1, 2, choice=1)], 10, 1, final=True)
        self.assertIsNone(interim[3].weighted_score)
        self.assertEqual(final[3].weighted_score, 0)

    def test_invalid_vote_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "choice and weight"):
            score_items([1, 2], [PairVote(1, 2, choice=6)], 10, 1)
