# Unit: Pairing Engine

## Purpose

Decide **who compares which pair**, and refuse — loudly, in numbers — when the
classroom's shape cannot support what was asked for.

## Responsibilities

- Solve feasibility (§8.2): given group sizes and a target coverage, return the
  highest coverage `R` and the resulting workload `k` that satisfy all three
  constraints, or raise.
- Allocate group-vs-group comparisons to evaluators, upholding INV-1 … INV-5.
- Enumerate within-group comparisons for individual evaluation (§8.3).
- Report what individual evaluation will look like for a given group size,
  including when it is impossible (m ≤ 2) or unreliable (m = 3).
- Randomise and **record** which item was shown on the left (FR-PAIR-08).

## NOT Responsible For

- Turning comparisons into scores → **Scoring Engine**
- Persisting anything → `app/utils.py` and the repositories
- Deciding who may *see* an allocation → the authorization layer
- Notifying students that pairs changed → Notification Service
- Storing the seed → the `assignment` row owns `pairing_seed`

## Dependencies

- **Depends on:** `app.domain` only. No database, no clock, no globals — the
  engine is a pure function so that thousands of random classrooms can be
  thrown at it in under two seconds.
- **Used by:** `app.services.AssignmentService.publish`, `app.utils`

## Key Business Rules

Every rule below has a test. The test file and name are given so a red test
points straight back here.

| Rule | Test |
|---|---|
| Coverage and workload are derived from each other, never both fixed (D3) | `test_large_room_reaches_the_default_coverage_of_five` |
| An impossible target is lowered, and the reason states the figures (FR-PAIR-05) | `test_a_lowered_coverage_is_explained_in_numbers_not_just_warned_about` |
| The student time budget caps coverage (constraint 2) | `test_max_workload_caps_coverage_even_when_the_room_is_large` |
| A classroom with fewer than 3 groups is refused — with 2, every student sits inside the only pair (OQ-8) | `test_a_two_group_classroom_is_refused_because_nobody_is_eligible_to_judge` |
| **INV-1** No evaluator judges a pair containing their own item (FR-PAIR-02/03) | `test_no_evaluator_is_ever_asked_to_judge_their_own_group` |
| **INV-2** No evaluator gets the same pair twice per criterion (FR-PAIR-07) | `test_no_evaluator_receives_the_same_pair_twice_in_one_criterion` |
| **INV-3** Coverage differs by ≤ 1 across pairs (FR-PAIR-06) | `test_coverage_is_balanced_across_every_pair` |
| **INV-4** Workload differs by ≤ 1 across evaluators | `test_workload_is_balanced_across_every_evaluator` |
| **INV-5** Same seed → identical allocation (FR-PAIR-09) | `test_the_same_seed_reproduces_the_identical_allocation` |
| Left/right position is randomised and stored (FR-PAIR-08/D8) | `test_each_pair_records_which_item_was_shown_on_the_left` |
| Individual coverage is `m − 2`, a consequence of group size (D4/§8.3) | `test_individual_plan_matches_the_table_in_the_prd` |
| Groups of ≤ 2 get no individual evaluation (FR-PAIR-12) | `test_groups_of_two_or_fewer_get_no_individual_evaluation` |
| Groups of 3 are always flagged low confidence (FR-PAIR-13) | `test_a_group_of_three_is_always_flagged_low_confidence` |
| A workload cap trims pairs and reports the lower coverage (FR-PAIR-14) | `test_workload_cap_trims_pairs_and_reports_the_lower_coverage` |

Invariants are additionally checked by `backend/tests/property/` across
randomly generated classrooms (3–8 groups × 3–8 members × coverage 1–6), which
is what NFR-MAINT-02 asks for.

## Design notes worth keeping

### Allocation is demand-first, workload-second

An earlier implementation handed out per-student workload quotas up front, then
filled pairs. The property tests killed it: in a class of 4 + 4 + 2, only the
two members of the small group may judge `{g1, g2}`, and an eligibility-blind
quota happily gave both of them zero — stranding the slot and reporting the
whole classroom as infeasible.

Filling pairs first and choosing the least-loaded eligible evaluator for each
slot removes that failure mode rather than patching it.

### Greedy alone cannot reach INV-4

Late in a round, every lightly-loaded evaluator may already have judged the
pair being handed out, so a heavier one takes it and the gap grows to 2. The
`_rebalance` pass fixes this by searching for an **augmenting chain** —
busiest → intermediary → … → idlest — where each hop is one legal handover.
Everyone in the middle gives one away and takes one back, so only the two ends
change load.

A single direct handover is not enough: it gets stuck whenever the idle
evaluator's own group appears in *all* of the busy evaluator's pairs, even
though a legal rearrangement exists. That case was also found by the property
tests, at 4 groups × 6 members × coverage 4.

### Seeding

`seeded_rng` hashes its inputs with SHA-256 rather than calling `hash()`.
Python salts string hashing per process, so a `hash()`-seeded RNG would give a
different allocation on every run and quietly destroy FR-PAIR-09.

## Key Stories

- US-04 — See feasibility, then publish pairs
- US-05 — See what I have been asked to evaluate
- US-09 — Find the comparisons I cannot trust (FR-PAIR-10, not built yet)

## Bolt Type

- [x] **DDD Construction** — the domain logic *is* the product here. Feasibility
      and the invariants are the reason the system is worth building.
- [ ] Simple Construction

## Human Checkpoint

Can this unit be built without knowing how the Scoring Engine works? **Yes.** It
never sees a choice value, a weight or a mark; it only emits assignments. The
only shared vocabulary is `PairAssignment`, and specifically
`display_left_item_id` — which pairing writes and scoring reads.

## Open Questions

- **OQ-8** — a classroom with exactly 2 groups. The PRD's default is "warn but
  allow"; this engine **refuses**, because with two groups every student is
  inside the single pair and no student is eligible to judge it. Allowing it
  would mean instructor-only evaluation, which is a different feature. Needs a
  product decision before M2.
- **FR-PAIR-10** ("ส่งประเมินเพิ่ม") is not implemented. It needs to draw from
  evaluators who have not already judged that pair, which is `already`
  bookkeeping the engine currently throws away after allocation.
