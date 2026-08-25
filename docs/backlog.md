# PairEval — Product Backlog

> These are written to be pasted into GitHub Issues one-for-one: title, body,
> labels. They are kept here as well so the backlog is reviewable in a diff and
> readable by an agent.
>
> Labels used: `user-story`, `bug`, `enhancement`, `tech-debt`
>
> **Not yet on GitHub.** `gh` is not installed on the machine this was written
> on, so the issues have not been created. Creating them is one command each
> once someone with push rights runs `gh auth login`.

## Definition of Done (applies to every story)

- [ ] Behaviour matches every acceptance criterion
- [ ] Unit tests cover the business rules of this story
- [ ] At least one E2E test covers one AC
- [ ] Reviewed by another group member
- [ ] Deployed to staging and usable there
- [ ] No secret, `.db` file or `__pycache__` in the diff

---

## Sprint 1

### US-01 — Create a classroom
`user-story`

**Story.** As an **instructor**, I want to create a classroom with a timezone
and a list of allowed email domains, so that only my own students can sign in
and every deadline shows in local time.

**Acceptance criteria**
- Given I am signed in as an instructor, when I submit a name and timezone, then the classroom is created and I am its OWNER.
- Given a name that would produce a slug already in use, when I submit, then I get 409 and no classroom is created.
- Given `allowedEmailDomains` is empty, when a user from any domain signs in, then they are **rejected** — the empty case fails closed (FR-AUTH-02).
- Given a deadline stored as UTC, when it is displayed, then it is shown in the classroom timezone (FR-ASSIGN-05).

**Traces:** FR-CLASS-01, FR-AUTH-02, FR-ASSIGN-05 · `POST /api/classrooms`

---

### US-02 — Import a roster from CSV
`user-story`

**Story.** As a **TA**, I want to upload a CSV of students and their groups, so
that I do not type 200 names by hand.

**Acceptance criteria**
- Given a CSV with headers `email, group_name` in any letter case, when I import, then every row is accepted.
- Given a CSV of 100 rows where line 42 has a malformed email, when I import, then **no row is written** and the error names "row 42" (FR-CLASS-02).
- Given `Somchai.A+x@uni.ac.th` in the roster, when that person signs in as `somchaia@uni.ac.th`, then they are matched to their roster row (FR-AUTH-03).
- Given two rows whose emails normalise to the same address, when I import, then it is reported as a duplicate and the file is rejected.
- Given a group with only one member, when I import, then the file is accepted and a warning names that group.
- Given a cell beginning `=`, `+`, `-` or `@`, when it is imported or exported, then it is stored prefixed with `'` so Excel will not execute it (FR-SEC-04).

**Traces:** FR-CLASS-01/02/03, FR-AUTH-03, FR-SEC-04 · `POST /api/classrooms/{id}/roster:import`

**Status:** engine done and tested (`backend/app/roster.py`, 28 tests). The API
route and the `email_normalized` column are not built yet.

---

### US-03 — Define an assignment and its criteria
`user-story`

**Story.** As an **instructor**, I want to define group and individual criteria
with weights, so that the final mark reflects what I actually care about.

**Acceptance criteria**
- Given criteria whose weights total 100% ± 0.01 on each side, when I save, then it is accepted.
- Given weights totalling 90%, when I try to publish, then I get 422 and the message names the side and the total (FR-ASSIGN-02).
- Given `individual_max_score = 0`, when I publish, then no individual pairs are generated at all (FR-ASSIGN-07).
- Given the assignment is PUBLISHED, when I try to edit criteria, then it is refused until I unpublish (FR-ASSIGN-03).

**Traces:** FR-ASSIGN-01/02/03/07

---

### US-04 — See feasibility, then publish pairs
`user-story`

**Story.** As an **instructor**, I want to see how many comparisons each pair
and each student will get *before* I publish, so that I am not surprised by a
coverage the room cannot support.

**Acceptance criteria**
- Given 200 students in 10 groups with target coverage 5, when I check feasibility, then it reports coverage 5 and 2 pairs per student (§8.2 example 1).
- Given 12 students in 3 groups with target coverage 5, when I check feasibility, then it reports coverage **4**, 1 pair per student, and a reason containing both numbers (§8.2 example 2, FR-PAIR-05).
- Given feasibility reports a reduction, when I publish without acknowledging it, then publish is refused.
- Given I publish twice with the same seed, when I compare the two allocations, then they are identical (FR-PAIR-09).
- Given any published allocation, when I check it, then no evaluator has a pair containing their own group, no evaluator has the same pair twice, coverage differs by at most 1 between pairs, and workload differs by at most 1 between students (INV-1 … INV-4).

**Traces:** FR-PAIR-01/02/04/05/06/07/09, §8.2, §8.4

**Status:** engine done and tested, including property tests over thousands of
random classroom shapes (`backend/tests/property/`).

---

### US-05 — See what I have been asked to evaluate
`user-story`

**Story.** As a **student**, I want one page listing every comparison assigned
to me for a criterion, so that I can finish in one sitting.

**Acceptance criteria**
- Given I open the page, when it loads, then every criterion appears as its own section, all on one page (FR-EVAL-01).
- Given a pair, when it renders, then both item names and both artifact links are shown (FR-EVAL-02).
- Given the assignment has no artifact link, when a pair renders, then it says the instructor has not provided one.
- Given a criterion with 5 assigned pairs and 3 answered, when the page loads, then it shows `3 / 5` (FR-EVAL-07).
- Given my group has 2 members, when I open the individual page, then it is not shown and the reason is explained (FR-EVAL-12).

**Traces:** FR-EVAL-01/02/07/12

---

### US-06 — Answer a comparison without losing work
`user-story`

**Story.** As a **student**, I want my answers saved as I go, so that a dropped
connection does not cost me fifteen minutes.

**Acceptance criteria**
- Given I pick an option, when 2 seconds pass, then it is saved and "บันทึกแล้ว เมื่อ HH:MM" appears (FR-EVAL-04).
- Given I close the browser mid-way, when I reopen the page, then my previous answers are still selected.
- Given the same save request is retried, when it arrives twice, then the result is identical (FR-API-01).
- Given the scale, when it renders, then there are 6 options with **no neutral middle**, each with a text label, reachable by arrow keys (D1, FR-EVAL-03, FR-A11Y-01/02).
- Given a saved draft that was never submitted, when scores are computed, then it is not counted (FR-EVAL-09, DR-01).

**Traces:** FR-EVAL-03/04/09, FR-API-01, FR-A11Y-01/02/06

---

### US-07 — Submit, and change my mind before the deadline
`user-story`

**Story.** As a **student**, I want to re-submit after thinking again, so that
one careless click does not lock in a mark for a classmate.

**Acceptance criteria**
- Given I have submitted, when I change an answer and submit again, then the latest submission is the one scored.
- Given I submit three times, when the audit log is read, then it holds three records (FR-EVAL-06).
- Given I have answered 4 of 6, when I press Submit, then it warns how many are unanswered but still lets me submit (FR-EVAL-05).
- Given the deadline has passed, when I try to submit, then I get 409 and the page becomes read-only (FR-EVAL-08).
- Given I double-tap Submit, when both requests arrive with the same `Idempotency-Key`, then only one submission is recorded (FR-API-02).

**Traces:** FR-EVAL-05/06/08, FR-API-02

---

### US-08 — See my own score, and only my own
`user-story`

**Story.** As a **student**, I want to see my score and my participation, so
that I know where I stand — without being able to work out who marked me down.

**Acceptance criteria**
- Given fewer than `k_min` (default 3) evaluators have submitted about me, when I open my score, then it says there is not enough data yet (FR-ANON-02).
- Given the assignment is not finalised, when my score displays, then it is labelled provisional (FR-SCORE-07).
- Given I check my score on two different days, when I compare, then no history, graph or delta is available (FR-ANON-03).
- Given my participation is 0.60 with a threshold of 0.90, when my score displays, then the multiplier shows as 0.667 and both numbers are visible (FR-SCORE-13).
- Given I query any endpoint, when I look for evaluator identity, then it is nowhere in the response (FR-ANON-01).

**Traces:** FR-ANON-01/02/03, FR-SCORE-07/13, FR-REPORT-06

---

### US-09 — Find the comparisons I cannot trust
`user-story`

**Story.** As an **instructor**, I want to see which pairs got too few
comparisons, so that I can send more evaluators before I finalise.

**Acceptance criteria**
- Given an item with fewer than `min_comparisons` submitted, when I open the report, then it is flagged `LOW_CONFIDENCE` (FR-SCORE-05).
- Given a flagged item, when I try to auto-finalise, then it is held back for a decision.
- Given a pair needing more coverage, when I press "ส่งประเมินเพิ่ม" with a count, then that many evaluators who have **not** already judged that pair are picked (FR-PAIR-10).
- Given quality signals fire, when the report renders, then nothing is dropped or reweighted automatically (FR-QS-01).

**Traces:** FR-REPORT-03/04, FR-SCORE-05, FR-PAIR-10, FR-QS-01

---

### US-10 — Finalise, and be able to explain it later
`user-story`

**Story.** As an **instructor**, I want finalised scores to snapshot their own
inputs, so that I can answer an appeal in three months even if the formula has
changed since.

**Acceptance criteria**
- Given I finalise, when the snapshot is written, then it holds both the inputs and the outputs plus the formula version (FR-SCORE-09).
- Given I override a score, when I save, then a reason is mandatory and an audit record is written (FR-SCORE-08, FR-AUDIT-01).
- Given the same stored rows, when the calculation is re-run, then every decimal place matches (FR-SCORE-10).
- Given a member submitted nothing, when their group's score is computed, then the group score is unchanged (FR-SCORE-11).

**Traces:** FR-SCORE-08/09/10/11, FR-AUDIT-01/02/03

---

## Edge cases raised by AI, and what we decided

Stories were written first, then an AI was asked what could go wrong in
production. Three buckets — the middle one is the point of the exercise.

### รับ → became a requirement

| Suggestion | Where it landed |
|---|---|
| Coverage 5 is impossible in small classes; the engine must lower it and say so | US-04 AC 2, `solve_group_feasibility` |
| A student in a two-person group cannot be peer-evaluated at all | US-05 AC 5, `individual_plan` |
| A daily-updating score lets a student infer who just submitted | US-08 AC 3 (FR-ANON-03) |
| An exported CSV cell starting with `=` executes when the instructor opens it | US-02 AC 6 |
| `Somchai.A+x@` and `somchaia@` are the same person and would double-import | US-02 AC 3/4 |

### ไม่รับ → declined, with the reason

| Suggestion | Why not |
|---|---|
| "Auto-exclude evaluators who straight-line their answers" | FR-QS-01 forbids it. Quality signals inform an instructor; they do not silently delete a student's opinion. A false positive would be invisible to everyone. |
| "Add a *มีคุณภาพเท่ากัน* middle option — students complain when two projects are similar" | D1 exists precisely because of this. A neutral button is what people press to avoid deciding, and a column of neutral answers separates nobody. The complaint is real; the fix is not. |
| "Normalise each criterion so the group scores sum to 1" | D2. With 10 groups that gives everyone ~1.5 out of 15. It measures relative share, not quality. |
| "Let a student see which teammate rated them lowest so they can improve" | Kills FR-ANON-01, which §19 lists as un-cuttable. Feedback with a name attached stops being honest. |
| "Cache generated pairs and reuse them across assignments to save compute" | Pair generation for 200 students takes well under the 10s budget (NFR-PERF-04). Caching would trade a non-problem for a stale-data bug. |
| "Let instructors delete an assignment outright" | DR-02/FR-AUDIT-03. Submitted comparisons are evidence in an appeal. Archive, never delete. |

### ยังไม่ตัดสิน → `tech-debt`

| Suggestion | Waiting on |
|---|---|
| Bradley–Terry instead of the weighted mean | §9.6 defers to v2.0. Raw comparisons are stored, so it can be computed retroactively. |
| Offline queue for flaky campus wifi (FR-EVAL-13) | Only worth it if drop-outs actually show up in the pilot. |
| Kendall's W for rater agreement (QS-07) | Needs one real semester of data before the 0.2 threshold means anything. |

---

## Known defects and debt in the current code

### ~~BUG-01 — Assignment scores are stored as `Float`~~ — fixed
`bug`

`backend/app/models.py` declared `group_score`, `individual_score`,
`instructor_weight` and `Criteria.weight` as `Float`, contradicting DR-04. The
engine is `Decimal` throughout, so the precision was lost only at the storage
boundary — which is exactly where a mark gets written into a grade document.

**Fixed:** columns are `Numeric`, and the matching Pydantic fields are
`Decimal`, so the value stays exact across the API boundary too. No migration
was needed — the dev database is recreated from the models and was never
supposed to be in version control.

### ~~BUG-02 — `orm_mode` is Pydantic v1 syntax~~ — fixed
`bug`

`backend/app/schemas.py` used `class Config: orm_mode = True` while
`requirements.txt` pins `pydantic>=2.0.0`, where the key is `from_attributes`.

**Fixed:** replaced with `model_config = ConfigDict(from_attributes=True)` in
all six schemas. Verified by booting the app under
`python3 -W error::DeprecationWarning`.

### BUG-03 — `Pair` rows had no evaluator
`bug`

`utils.generate_pairs()` emitted `C(n,2) × coverage` rows with no evaluator
attached, no exclusion of an evaluator's own group, no feasibility check, no
duplicate guard and no position randomisation — violating FR-PAIR-02, -03, -06,
-07 and -08 at once. Nobody could have answered those rows.

**Fixed:** `utils.py` now delegates to `app/pairing.py`; `models.Pair` gained
`evaluator_id`, `display_left_item_id` and `generation`. The old function
raises `NotImplementedError` with a pointer, rather than being deleted silently.

### TD-01 — No `Comparison` table
`tech-debt`

The scoring engine is complete and tested but has nothing to read: `COMPARISON`
and `COMPARISON_REVISION` from `docs/erd.md` do not exist yet. Blocks US-06,
US-07, US-08.

### TD-02 — No roles, no authorization layer
`tech-debt`

`CLASSROOM_MEMBER` and its role column are not modelled, so §3's permission
matrix cannot be enforced and FR-AUTHZ-01/02 are unimplemented. §19 lists these
among the three things that must not be cut.

### TD-03 — No audit log
`tech-debt`

FR-AUDIT-01/02/03 unimplemented. Also un-cuttable per §19.

### TD-04 — `project/` is a different domain
`tech-debt`

`project/` holds the room-booking harness from the WS-03 handout. It is a
working example of the test patterns, but it is not PairEval and should not
grow. The real harness is `backend/tests/`.
