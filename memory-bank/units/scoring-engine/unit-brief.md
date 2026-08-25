# Unit: Scoring Engine

## Purpose

Turn stored comparisons into marks that an instructor can defend to a student's
face three months later.

## Responsibilities

- Map a 6-point choice onto the two items it was about, replaying the recorded
  screen positions (§9.1).
- Compute the quality index `q` per (item, criterion) as a weighted mean (§9.2).
- Map `q` to a score ratio through band mapping, then weight it by criterion and
  side maximum (§9.3).
- Compute the participation ratio `p` and multiplier `M`, and apply it to a
  student's personal total (§9.4).
- Flag anything too thin to defend (`LOW_CONFIDENCE`, FR-SCORE-05).
- Validate that criteria weights total 100% per side (FR-ASSIGN-02).

## NOT Responsible For

- Deciding who compares what → **Pairing Engine**
- Deciding whether a score is *shown* → the anonymity layer (FR-ANON-02)
- Instructor overrides and finalisation → `AssignmentService` + `score_override`
- Quality signals QS-01 … QS-07 → a separate integrity unit, not built yet
- Rounding for a grade document → the caller; the engine keeps full precision

## Dependencies

- **Depends on:** `app.domain` only. Pure functions, no I/O, no clock (AR-01) —
  which is what makes FR-SCORE-10 ("rerun gives identical digits") true rather
  than aspirational.
- **Used by:** `app.services.AssignmentService`, reports, export

## Key Business Rules

| Rule | Test |
|---|---|
| Each choice splits exactly one point between the two items (§9.1) | `test_every_choice_splits_exactly_one_point_between_the_two_items` |
| There is no neutral option — no choice splits 50/50 (D1) | `test_scale_has_no_neutral_option_so_no_choice_splits_the_point_evenly` |
| Points follow the *displayed* position, not stored item order (FR-PAIR-08) | `test_points_follow_the_displayed_position_not_the_stored_item_order` |
| `q` is the weighted mean of points received (§9.2) | `test_quality_index_is_the_weighted_mean_of_the_points_an_item_received` |
| Only `SUBMITTED` comparisons are scored (DR-01) | `test_draft_and_excluded_comparisons_never_reach_a_score` |
| Instructor weight is a float in the mean, not a repeated vote (D6) | `test_instructor_weight_shifts_the_mean_without_inflating_the_comparison_count` |
| Below `min_comparisons` → `LOW_CONFIDENCE` (FR-SCORE-05) | `test_item_below_min_comparisons_is_flagged_low_confidence` |
| No comparisons → no `q`, not a zero | `test_item_with_no_comparisons_has_no_quality_index_rather_than_zero` |
| Band mapping puts q=0 at the floor and q=1 at the ceiling (§9.3) | `test_band_mapping_puts_q_zero_at_the_floor_and_q_one_at_the_ceiling` |
| Scores are never normalised to sum to 1 (D2) | `test_band_mapping_never_normalises_scores_to_sum_to_one` |
| A `q` outside [0, 1] is rejected, not clamped | `test_quality_index_outside_zero_to_one_is_rejected_rather_than_clamped` |
| Criteria weights must total 100% ± 0.01 per side (FR-ASSIGN-02) | `test_criteria_weights_must_total_one_hundred_percent` |
| A side with no criteria is switched off, not invalid (FR-ASSIGN-07) | `test_a_side_with_no_criteria_is_switched_off_rather_than_invalid` |
| `M = min(1, p / threshold)`, applied to the personal total only (§9.4) | `test_participation_at_or_above_the_threshold_gives_a_full_multiplier` |
| A student assigned nothing is not penalised | `test_a_student_who_was_assigned_nothing_is_not_penalised` |
| Submitting more than assigned is impossible data, and rejected | `test_submitting_more_than_assigned_is_rejected_as_impossible_data` |
| **A member's absence never reduces their group's score (FR-SCORE-11/D5)** | `test_a_members_missing_participation_does_not_reduce_the_group_score` |

### Golden tests — PRD §9.5 worked example

The PRD's worked example is reproduced digit for digit. If the formula is ever
changed by accident, these are what go red.

| Case | Expected | Test |
|---|---|---|
| Group Aurora | 12.798 / 15 | `test_golden_group_aurora_scores_12_798_out_of_15` |
| นก, participated fully | 16.93 / 20 | `test_golden_student_nok_who_evaluated_everything_scores_16_93_out_of_20` |
| ต้น, submitted 9 of 15 | 10.97 / 20 | `test_golden_student_ton_who_skipped_half_scores_10_97_out_of_20` |

## Design notes worth keeping

### `Decimal` everywhere, and why the golden tests need it

`0.6 + 0.4 * 0.72` in binary floating point is `0.888...0000000000001`. Held in
a grade document, that becomes a support ticket. DR-04 says `numeric`; the
engine says `Decimal` from input to output, and rounds only in `quantize()` at
the display boundary.

The one place this is still violated is storage: `Assignment.group_score` is
`Float` in `backend/app/models.py`. Tracked as BUG-01.

### Position replay is not a detail

`points_for_items` reads `display_left_item_id`, not `item_a_id`. Reading the
choice against stored order instead would invert every comparison whose coin
flip came up tails — roughly half of them — and it would do it silently, with
no error anywhere. It is the single most dangerous line in the unit, which is
why it has its own test.

### Missing evidence contributes nothing, not a floor score

An item with no comparisons gets `q = None` and adds `0` to the total, rather
than the 60% floor. Awarding the floor to work nobody judged would hide the
gap, and the gap is exactly what `LOW_CONFIDENCE` exists to surface.

## Key Stories

- US-08 — See my own score, and only my own
- US-09 — Find the comparisons I cannot trust
- US-10 — Finalise, and be able to explain it later

## Bolt Type

- [x] **DDD Construction** — every line is a policy decision with a paper trail
      in §9 and the decision log.
- [ ] Simple Construction

## Human Checkpoint

Can this be built without knowing how pairing allocates? **Yes.** It consumes
`Comparison` objects and never asks how they came to exist. The one coupling is
`display_left_item_id`, and it is a data field, not a behaviour.

## Open Questions

- **OQ-1** — is `score_floor = 0.60` right for this course's marking scheme?
  Configurable per assignment; default unchanged pending an instructor decision.
- **OQ-2** — should `M` multiply the whole score or only the individual
  component? Currently the whole score, per the PRD default. This is a course
  policy question, not a technical one, and it changes marks materially.
- **QS-01 … QS-07** — integrity signals are specified but not implemented. When
  they are, FR-QS-01 must hold: they inform, they never auto-exclude.
