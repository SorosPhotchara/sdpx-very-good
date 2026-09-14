# Unit: Scoring Engine

## Purpose

Turn stored comparisons into marks that an instructor can defend to a student's
face three months later.

## Responsibilities

- Map a 6-point choice onto the two items it was about, replaying the recorded
  screen positions (PRD §9.1).
- Compute the quality index `q` per (item, criterion) as a weighted mean (§9.2).
- Map `q` to a score ratio through band mapping, then weight it by criterion and
  side maximum (§9.3).
- Compute the participation ratio `p` and multiplier `M`, and apply `M` to a
  student's personal total (§9.4).
- Flag anything too thin to defend (`LOW_CONFIDENCE`, FR-SCORE-05).
- Validate that criteria weights total 100% ± 0.01 per side (FR-ASSIGN-02).

## NOT Responsible For

- Deciding who compares what → **Pairing Engine**
- Deciding whether a score is *shown* to a student → the anonymity layer
  (FR-ANON-02, the `k_min` check behind `GET /my-score`)
- Instructor overrides and finalisation → `score_override` and the finalize flow
- Quality signals QS-01 … QS-07 → a separate integrity unit, not planned yet
- Rounding for a grade document → the caller; the engine keeps full precision

## Dependencies

- **Depends on:** nothing outside its own domain types. Pure functions, no I/O,
  no clock (AR-01) — which is what makes FR-SCORE-10 ("rerun gives identical
  digits") true rather than aspirational.
- **Used by:** the daily 02:00 recompute and on-demand recompute (FR-SCORE-06),
  `GET /api/assignments/{assignmentId}/my-score`,
  `GET /api/assignments/{assignmentId}/reports/group`, and the weight check in
  `POST /api/assignments/{assignmentId}:publish` (`docs/openapi.yaml`).

## Key Business Rules

> No code exists yet. Each rule becomes a test in WS-03; the name on the right
> is the test name to use.

| Rule | Planned test |
|---|---|
| Each choice splits exactly one point between the two items (§9.1) | `test_every_choice_splits_exactly_one_point_between_the_two_items` |
| There is no neutral option — no choice splits 50/50 (D1) | `test_scale_has_no_neutral_option_so_no_choice_splits_the_point_evenly` |
| Points follow the *displayed* position, not stored item order (FR-PAIR-08) | `test_points_follow_the_displayed_position_not_the_stored_item_order` |
| `q` is the weighted mean of points received (§9.2) | `test_quality_index_is_the_weighted_mean_of_the_points_an_item_received` |
| Only submitted answers are scored, each at its latest submitted version; drafts and `EXCLUDED` never (DR-01, FR-EVAL-06) | `test_only_the_latest_submitted_version_of_each_answer_is_scored` |
| Instructor weight is a float in the mean, not a repeated vote (D6) | `test_instructor_weight_shifts_the_mean_without_inflating_the_comparison_count` |
| Below `min_comparisons` → `LOW_CONFIDENCE` (FR-SCORE-05) | `test_item_below_min_comparisons_is_flagged_low_confidence` |
| No comparisons → no `q` and no score, not a zero | `test_item_with_no_comparisons_has_no_quality_index_rather_than_zero` |
| A total with any criterion still unscored is `None`, not a partial sum | `test_a_total_is_unknown_while_any_criterion_has_no_score` |
| Band mapping puts q=0 at the floor and q=1 at the ceiling (§9.3) | `test_band_mapping_puts_q_zero_at_the_floor_and_q_one_at_the_ceiling` |
| Scores are never normalised to sum to 1 (D2) | `test_band_mapping_never_normalises_scores_to_sum_to_one` |
| A `q` outside [0, 1] is rejected, not clamped | `test_quality_index_outside_zero_to_one_is_rejected_rather_than_clamped` |
| Criteria weights must total 100% ± 0.01 per side: 99.99 passes, 99.98 fails (FR-ASSIGN-02, US-ASSIGN-01) | `test_criteria_weights_must_total_one_hundred_percent` |
| A side with max score 0 has no criteria and is skipped (FR-ASSIGN-07) | `test_a_side_with_max_score_zero_is_switched_off_rather_than_invalid` |
| `M = min(1, p / threshold)`, applied to the personal total only (§9.4) | `test_participation_at_or_above_the_threshold_gives_a_full_multiplier` |
| A student assigned nothing is not penalised | `test_a_student_who_was_assigned_nothing_is_not_penalised` |
| Submitting more than assigned is impossible data, and rejected | `test_submitting_more_than_assigned_is_rejected_as_impossible_data` |
| **A member's absence never reduces their group's score (FR-SCORE-11, D5)** | `test_a_members_missing_participation_does_not_reduce_the_group_score` |

### Golden tests — PRD §9.5 worked example

NFR-MAINT-01 requires the worked example as golden tests, reproduced digit for
digit. If the formula is ever changed by accident, these go red.

| Case | Expected | Planned test |
|---|---|---|
| Group Aurora | 12.798 / 15 | `test_golden_group_aurora_scores_12_798_out_of_15` |
| นก, participated fully | 16.93 / 20 | `test_golden_student_nok_who_evaluated_everything_scores_16_93_out_of_20` |
| ต้น, submitted 9 of 15 | 10.97 / 20 | `test_golden_student_ton_who_skipped_half_scores_10_97_out_of_20` |

## Notes for implementation

- **`Decimal` everywhere.** `0.6 + 0.4 * 0.72` in binary floating point is not
  exactly `0.888`; held in a grade document, that becomes a support ticket.
  DR-04 says `numeric` in the database (`docs/erd.md`); the engine uses
  `Decimal` from input to output and rounds only at the display boundary. The
  weight check must use `Decimal` too, or `33.33 + 33.33 + 33.34` can miss 100.
- **Position replay is the most dangerous line.** Points come from
  `display_left_item_id`, not `item_a_id`. Reading the choice against stored
  order would silently invert every comparison whose left/right coin flip came
  up the other way — roughly half of them.
- **Missing evidence is shown as missing.** An item with no comparisons gets no
  `q` and no score, rather than the 60% floor. Awarding the floor to work nobody
  judged would hide the gap that `LOW_CONFIDENCE` exists to surface. The Group
  Summary report shows such a cell as `null`, and the row total as `null`.

## Key Stories

- US-SCORE-01 — Student views their own scores
- US-REPORT-01 — Instructor views the Group Summary report
- US-ASSIGN-01 — Criteria weight check at publish

## Bolt Type

- [x] **DDD Construction** — every line is a policy decision with a paper trail
      in PRD §9 and the decision log.
- [ ] Simple Construction

## Human Checkpoint

Can this be built without knowing how pairing allocates? **Yes.** It consumes
comparisons and never asks how they came to exist. The one coupling is
`display_left_item_id`, and it is a data field, not a behaviour.

## Open Questions

- **OQ-1** (PRD §17) — is `score_floor = 0.60` right for this course? It is
  configurable per assignment; the default stays until the instructor decides.
- **OQ-2** — should `M` multiply the whole score or only the individual
  component? The PRD default is the whole score. This is course policy, not a
  technical question, and it changes marks materially.
- **Q3** (`docs/open-questions.md`) — do instructor comparisons count toward
  `min_comparisons`, and as 1 or as `instructor_weight`? The D6 rule above
  counts each as 1, which is provisional until Q3 is answered.
