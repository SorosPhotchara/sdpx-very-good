# Intent: PairEval

## Intent Statement

Let a university mark group work by **pairwise comparison** — "is A or B
better?" instead of "how many marks is A worth?" — so that individual
contribution inside a group can be told apart with evidence, and so that the
instructor, not the algorithm, decides the final mark.

## Business Context

**Problem.** Three failures show up every semester when group work is graded
directly:

| Failure | What it looks like |
|---|---|
| Absolute scoring bias | The first project marked and the last are held to different standards, and each is anchored to whatever was marked just before. |
| Free riders | A member who did nothing receives the same mark as one who did everything, because the mark is attached to the group. |
| Peer rating inflation | Asked to score their friends out of 5, students give 5s. The data separates nobody. |

**Product hypothesis.** Comparing two things side by side is a task people do
consistently; scoring one thing alone is not. So the system records *only*
comparisons and synthesises marks afterwards.

**Users.** Instructors (owner + co-teacher), TAs, and students. Students are
the volume: 200 per classroom, mostly on phones, once or twice a semester.

**Value.** Marks that can be defended when a student appeals — because every
mark traces back to a stored set of comparisons and a formula anyone can read.

## Success Criteria

- [ ] **M3 — score dispersion.** Standard deviation of individual scores within
      a group ≥ 0.5 (out of 5). *This is the one that matters.* If everybody in
      a group still ends up with the same number, the product did not solve its
      problem, no matter how good the other metrics look.
- [ ] **M1 — participation** ≥ 90% of assigned comparisons submitted.
- [ ] **M2 — time on task** median ≤ 15 minutes per assignment.
- [ ] **M4 — instructor override rate** ≤ 5%. Higher means the formula
      disagrees with informed human judgement, and the formula is what is wrong.
- [ ] **M5 — dispute rate** ≤ 3% of students.
- [ ] **M6 — low-confidence items** ≤ 5%.

## Decisions Already Made

Do not reopen these without an ADR. They are listed here so an agent stops
proposing the alternative every time it reads the code.

| # | Decision | The thing that gets suggested instead |
|---|---|---|
| D1 | **6-point forced choice, no neutral option** | "Add a 'they're equal' button." A middle option is what people press to avoid deciding. |
| D2 | **Band mapping**, floor 0.60 → ceiling 1.00 | "Normalise so scores sum to 1." Ten groups then get ~1.5 out of 15. |
| D3 | **Coverage R and workload k derive from each other** | "Just fix both at 5." That is infeasible for most real class sizes. |
| D4 | **Individual coverage = m − 2** | "Require 5 comparisons per pair." Impossible in any group smaller than 7. |
| D5 | **Participation is a separate multiplier from earned score** | "Give non-participants zero." Not reviewing peers is not evidence your own work was bad. |
| D6 | **Instructor weight is a float in a weighted mean** | "Count the instructor's vote three times." That corrupts the comparison count. |
| D7 | **k-anonymity threshold before showing an individual score** | "Show it as soon as there's data." In a group of 3, one submission identifies the submitter. |
| D8 | **Left/right position randomised and stored** | "Just order by id." Evaluators have a systematic side bias. |

Also settled:

- **Python + FastAPI backend, React + Vite frontend.** See
  `memory-bank/standards/tech-stack.md`.
- **The engines are pure functions** (AR-01). Pairing and scoring take
  dataclasses and return dataclasses. No database, no clock, no globals.
- **`Decimal`, never `float`, for anything that becomes a mark** (DR-04).
- **The system never assigns a final grade.** It produces raw scores; the
  instructor decides (G3, A4).

## Out of Scope

Not in v1.0, and not worth arguing about during this course:

- LMS integration (LTI 1.3) — nobody has told us which LMS the university runs
- Native mobile app — responsive web is enough for a 15-minute task
- Multi-language UI — the first cohort is entirely Thai
- Bradley–Terry / Elo scoring — see §9.6; explainability beats statistical
  elegance when a student appeals. Raw comparisons are stored, so this can be
  computed retroactively in v2.0.
- Rubric text attached per criterion
- Evaluation across classrooms
- Assignment submission and file storage — that is the LMS's job

## Non-negotiable

§19 names three things that cannot be cut when time runs short, because none of
them can be retrofitted after real student data exists:

- **FR-ANON-01** — a student must never be able to learn who evaluated them,
  through the UI, the API, or an export.
- **FR-AUTHZ-01/02** — authorization is checked server-side on every request,
  and scoped to the classroom.
- **FR-AUDIT-01** — publish, regenerate, override, finalise and identity access
  are all logged, append-only.

None of the three is implemented yet. They are TD-02 and TD-03 in
`docs/backlog.md`.

## Status

**In Progress — WS-03.**

| Area | State |
|---|---|
| Pairing engine (§8) | ✅ Implemented, unit + property tested |
| Scoring engine (§9) | ✅ Implemented, unit + golden tested against §9.5 |
| Roster import (§7.2) | ✅ Engine implemented and tested; no API route yet |
| FastAPI CRUD | 🔨 Prototype: classrooms, students, groups, assignments, criteria |
| Comparison storage | ❌ TD-01 |
| Auth / authorization | ❌ TD-02 |
| Audit log | ❌ TD-03 |
| Frontend | 🔨 Landing page + classroom create; E2E smoke passing |
| Deploy | ❌ Not connected — see `memory-bank/standards/tech-stack.md` |
