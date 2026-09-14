# Unit: Pairing Engine

## Purpose

Decide **who compares which pair**, and refuse — loudly, in numbers — when the
classroom's shape cannot support what was asked for.

## Responsibilities

- Solve feasibility (PRD §8.2): given group sizes and a target coverage, return
  the highest coverage `R` and the resulting workload `k` that satisfy all three
  constraints, plus the coverage the allocation will really achieve (min–max).
- Allocate group-vs-group comparisons to evaluators, upholding INV-1 … INV-5.
- Enumerate within-group comparisons for individual evaluation (§8.3).
- Report what individual evaluation will look like for each group size,
  including when it is impossible (m ≤ 2), unreliable (m = 3), or sampled
  because it exceeds `max_workload`.
- Randomise and **record** which item is shown on the left (FR-PAIR-08).

## NOT Responsible For

- Turning comparisons into scores → **Scoring Engine**
- Persisting anything → the API's data layer (`pair_assignment` in `docs/erd.md`)
- Deciding who may *see* an allocation → the authorization layer
- Notifying students that pairs changed → notification service (FR-NOTIF-03)
- Storing the seed → the `assignment` row owns `pairing_seed`

## Dependencies

- **Depends on:** nothing outside its own domain types. A pure function —
  roster shape, settings, and seed in; plan and allocation out (AR-01) — so the
  property tests can throw thousands of random classrooms at it quickly.
- **Used by:** `GET /api/assignments/{assignmentId}/feasibility` (preview) and
  `POST /api/assignments/{assignmentId}:publish` (generation) in
  `docs/openapi.yaml`.

## Key Business Rules

> No code exists yet. Each rule becomes a test in WS-03; the name on the right
> is the test name to use, so a red test points straight back here.

| Rule | Planned test |
|---|---|
| Coverage and workload are derived from each other, never both fixed (D3) | `test_large_room_reaches_the_default_coverage_of_five` |
| An impossible target is lowered, and the reason states the figures (FR-PAIR-05) — e.g. 12 students in 3 groups of 4: "Each pair has only 4 eligible evaluators, so the maximum coverage is 4 per pair (not 5)." | `test_a_lowered_coverage_is_explained_in_numbers_not_just_warned_about` |
| The student time budget caps coverage (constraint 2) | `test_max_workload_caps_coverage_even_when_the_room_is_large` |
| Achieved coverage is reported, not only the target — 200 students in 10 groups: target 5, achieved 8–9 | `test_feasibility_reports_the_coverage_the_allocation_really_achieves` |
| A group side with coverage 0 is refused — with 2 groups every student sits inside the only pair (provisional, Q2) | `test_a_two_group_classroom_is_refused_because_nobody_is_eligible_to_judge` |
| **INV-1** No evaluator judges a pair containing their own item (FR-PAIR-02/03) | `test_no_evaluator_is_ever_asked_to_judge_their_own_group` |
| **INV-2** No evaluator gets the same pair twice per criterion (FR-PAIR-07) | `test_no_evaluator_receives_the_same_pair_twice_in_one_criterion` |
| **INV-3** Coverage differs by ≤ 1 across pairs (FR-PAIR-06) | `test_coverage_is_balanced_across_every_pair` |
| **INV-4** Workload differs by ≤ 1 across evaluators | `test_workload_is_balanced_across_every_evaluator` |
| **INV-5** Same seed → identical allocation (FR-PAIR-09) | `test_the_same_seed_reproduces_the_identical_allocation` |
| Left/right position is randomised and stored (FR-PAIR-08, D8) | `test_each_pair_records_which_item_was_shown_on_the_left` |
| Individual coverage is `m − 2` (D4, §8.3) | `test_individual_plan_matches_the_table_in_the_prd` |
| Groups of ≤ 2 get no individual evaluation (FR-PAIR-12) | `test_groups_of_two_or_fewer_get_no_individual_evaluation` |
| Groups of 3 are always flagged low confidence (FR-PAIR-13) | `test_a_group_of_three_is_always_flagged_low_confidence` |
| A workload cap trims pairs and reports the lower coverage (FR-PAIR-14) | `test_workload_cap_trims_pairs_and_reports_the_lower_coverage` |
| The number of pairs generated equals the previewed total (US-PUBLISH-01 AC1) | `test_publish_generates_exactly_the_previewed_number_of_pairs` |

INV-1 … INV-5 are also checked by property-based tests across randomly
generated classrooms (3–8 groups × 3–8 members × coverage 1–6), as NFR-MAINT-02
requires.

## Notes for implementation

- **Fill pairs first, then pick the least-loaded eligible evaluator.** Handing
  out per-student quotas up front can strand a pair that only a few people may
  judge. In a class of 4 + 4 + 2, only the 2 members of the small group may
  judge `{g1, g2}`; a quota that gives both of them zero leaves that slot
  empty and makes the whole classroom look infeasible.
- **Greedy allocation alone can break INV-4.** Late in a round, every
  lightly-loaded evaluator may already have judged the pair being handed out,
  so a heavier one takes it and the gap grows to 2. Plan a rebalance pass that
  moves work along a chain — busiest → intermediary → … → idlest — where each
  hop is one legal handover.
- **Seed with SHA-256 of the inputs, never Python's `hash()`.** Python salts
  string hashing per process, so a `hash()`-seeded generator gives a different
  allocation on every run and quietly breaks FR-PAIR-09.

## Key Stories

- US-PUBLISH-01 — See feasibility, then publish pairs
- US-EVAL-01 — Evaluate group pairs (reads the allocation)

## Bolt Type

- [x] **DDD Construction** — the domain logic *is* the product here. Feasibility
      and the invariants are the reason the system is worth building.
- [ ] Simple Construction

## Human Checkpoint

Can this unit be built without knowing how the Scoring Engine works? **Yes.** It
never sees a choice value, a weight or a mark; it only emits assignments. The
only shared vocabulary is `pair_assignment`, and specifically
`display_left_item_id` — which pairing writes and scoring reads.

## Open Questions

- **Q2** (`docs/open-questions.md`) — a classroom with exactly 2 groups. The
  PRD's default (OQ-8) is "warn but allow", but no student is eligible to judge
  the only pair. This unit refuses for now; the API returns
  `422 PAIRING_INFEASIBLE`, marked provisional.
- **Q3** — do extra pairs from instructors (`source = INSTRUCTOR_*`) count
  toward coverage balance (FR-PAIR-06)?
- **FR-PAIR-10** ("ส่งประเมินเพิ่ม") has no user story yet. When it does, the
  engine must remember who already judged each pair.
