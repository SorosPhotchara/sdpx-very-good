# Intent: Pairwise

## Intent Statement

Let a university mark group work by **pairwise comparison** — "is A or B
better?" instead of "how many marks is A worth?" — so that individual
contribution inside a group can be told apart with evidence, and so that the
instructor, not the algorithm, decides the final mark.

## Business Context

**Problem.** Three failures show up every semester when group work is graded
directly (PRD §1.1):

| Failure | What it looks like |
|---|---|
| Absolute scoring bias | The first project marked and the last are held to different standards, and each is anchored to whatever was marked just before. |
| Free riders | A member who did nothing receives the same mark as one who did everything, because the mark is attached to the group. |
| Peer rating inflation | Asked to score their friends out of 5, students give 5s. The data separates nobody. |

**Product hypothesis.** Comparing two things side by side is a task people do
consistently; scoring one thing alone is not. So the system records *only*
comparisons and synthesises marks afterwards.

**Users.** Instructors (owner + co-teacher), TAs, and students. Students are
the volume: up to 200 per classroom in up to 40 groups (A3), mostly on phones,
two or three times a semester.

**Value.** Marks that can be defended when a student appeals — because every
mark traces back to a stored set of comparisons and a formula anyone can read.

## Success Criteria

Measured after one semester of real use (PRD §1.4).

- [ ] **M3 — score dispersion.** Standard deviation of individual scores within
      a group ≥ 0.5 (out of 5). *This is the one that matters.* If everybody in
      a group still ends up with the same number, the product did not solve its
      problem, no matter how good the other metrics look.
- [ ] **M1 — participation** ≥ 90% of students submit everything assigned.
- [ ] **M2 — time on task** median ≤ 15 minutes per assignment.
- [ ] **M4 — instructor override rate** ≤ 5%. Higher means the formula
      disagrees with informed human judgement, and the formula is what is wrong.
- [ ] **M5 — dispute rate** ≤ 3% of students.
- [ ] **M6 — low-confidence items** ≤ 5%.

## Decisions Already Made

Do not reopen these without an ADR. They are listed here so an agent stops
proposing the alternative every time it reads the repository.

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

Also settled by the team (details in `memory-bank/standards/tech-stack.md` and
`docs/architecture.md`):

- **Stack.** React + Vite SPA on Vercel; FastAPI backend; **PostgreSQL**
  (switched from SQLite on 2026-09-14, before any backend code).
- **Sign-in.** Google OAuth 2.0 authorization code flow run by the server
  (`/api/auth/google/start` → Google → `/api/auth/google/callback`). Sessions
  are server-side in an `httpOnly` cookie, not bearer tokens.
- **The engines are pure functions** (AR-01): no database, no clock, no
  globals. Inputs in, results out.
- **`Decimal`, never `float`, for anything that becomes a mark** (DR-04).
- **Scores use each answer's latest submitted version** (FR-EVAL-06). Editing
  after submitting creates a draft; the last submitted value keeps counting
  until the next submit.
- **The system never assigns a final grade.** It produces raw scores; the
  instructor decides (G3, A4).

## Out of Scope

Not in v1.0, and not worth arguing about during this course:

- LMS integration (LTI 1.3) — nobody has told us which LMS the university runs
- Native mobile app — responsive web is enough for a 15-minute task
- Multi-language UI — the first cohort is entirely Thai
- Bradley–Terry / Elo scoring — see PRD §9.6; explainability beats statistical
  elegance when a student appeals. Raw comparisons are stored, so this can be
  computed retroactively later.
- Rubric text attached per criterion
- Evaluation across classrooms
- Assignment submission and file storage — that is the LMS's job
- Server-side rendering — PRD §6 draws an SSR web app, but it is not a MUST;
  the SPA stays

## Non-negotiable

PRD §19 names three things that cannot be cut when time runs short, because
none of them can be retrofitted after real student data exists:

- **FR-ANON-01** — a student must never be able to learn who evaluated them,
  through the UI, the API, or an export.
- **FR-AUTHZ-01/02** — authorization is checked server-side on every request,
  and scoped to the classroom.
- **FR-AUDIT-01** — publish, regenerate, override, finalise and identity access
  are all logged, append-only.

None of the three is implemented yet, because there is no backend yet.

## Where things are

| What | Where |
|---|---|
| Requirements (PRD v2.0) | `docs/prd.md` |
| User stories with acceptance criteria | `docs/user-stories.md` |
| Questions the PRD does not answer | `docs/open-questions.md` |
| Component diagram, auth flow | `docs/architecture.md` |
| Database schema | `docs/erd.md` |
| API contract | `docs/openapi.yaml` |
| UI rules, brand colours | `docs/ui-design.md` |
| Units | `memory-bank/units/*/unit-brief.md` |

## Status

**In Progress — WS-02.**

| Area | State |
|---|---|
| Frontend | ✅ Landing page live at `https://sdpx-very-good.vercel.app`, auto-deployed from `develop`; 4 unit tests (`bun test`) |
| Requirements & design | ✅ 9 user stories, architecture, ERD, OpenAPI (15 endpoints, lint passes) |
| Pairing engine | ⏳ Not started — rules in `units/pairing-engine` |
| Scoring engine | ⏳ Not started — rules in `units/scoring-engine` |
| Roster import | ⏳ Not started — rules in `units/roster-import` |
| Backend API, database, sign-in | ⏳ Not started; backend host not chosen |
| Audit log, notifications | ⏳ Not started |
| Open questions | Q1–Q6 waiting for the instructor (`docs/open-questions.md`) |
