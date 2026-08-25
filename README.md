# PairEval

Mark university group work by **pairwise comparison** — "is A or B better?"
instead of "how many marks is A worth?" — so that individual contribution
inside a group can be told apart with evidence, and the instructor, not the
algorithm, decides the final mark.

Full requirements: [`pairwise_evaluation_prd.md`](pairwise_evaluation_prd.md) ·
Intent and scope: [`memory-bank/intent.md`](memory-bank/intent.md)

## Why pairwise

Three things go wrong every semester when group work is graded directly: the
first project marked and the last are held to different standards; a member who
did nothing gets the same mark as one who did everything; and students asked to
score their friends out of 5 give 5s. Comparing two things side by side is a
task people do consistently. Scoring one thing alone is not.

## Quick start

Requires Python 3.12+ and Node 20+.

```bash
# backend
python3 -m pip install -r backend/requirements.txt
cd backend && python3 -m uvicorn app.main:app --reload     # http://localhost:8000

# frontend
cd frontend && npm install && npm run dev                  # http://localhost:5173

# tests — all three suites, about half a second
pytest

# end-to-end
cd frontend && npx playwright test
```

Copy [`.env.example`](.env.example) to `.env` before running anything that
needs credentials. Never put a real value in `.env.example`.

## Layout

| Path | What is in it |
|---|---|
| [`backend/app/`](backend/app/) | FastAPI service. `pairing.py`, `scoring.py` and `roster.py` are pure functions with no I/O — that is deliberate (AR-01). |
| [`backend/tests/`](backend/tests/) | The PairEval harness: unit, golden and property tests. |
| [`frontend/`](frontend/) | Vite + React + TypeScript, Tailwind. |
| [`frontend/tests/e2e/`](frontend/tests/e2e/) | Playwright smoke tests. |
| [`docs/`](docs/) | [architecture](docs/architecture.md) · [ERD](docs/erd.md) · [OpenAPI](docs/openapi.yaml) · [backlog](docs/backlog.md) · [wireframes](docs/wireframes/) · [open questions](docs/open-questions.md) |
| [`memory-bank/`](memory-bank/) | Intent, unit briefs, tech-stack decisions — reasons, not commands. |
| [`AGENTS.md`](AGENTS.md) | The rules an AI agent reads before touching this repo. |
| [`TEST_PLAN.md`](TEST_PLAN.md) | Which business rules are tested, which are not, and the fidelity check. |
| [`project/`](project/) | The WS-03 room-booking warm-up from the course handout. Not PairEval. |
| [`ws-01-before/`](ws-01-before/) | The WS-01 FizzBuzz agent-loop exercise. |

## Current status

| Area | State |
|---|---|
| Pairing engine (PRD §8) | ✅ Implemented · unit + property tested |
| Scoring engine (PRD §9) | ✅ Implemented · golden-tested against the §9.5 worked example |
| Roster import (PRD §7.2) | ✅ Engine done and tested · no API route yet |
| FastAPI CRUD | 🔨 Prototype: classrooms, students, groups, assignments, criteria, pairs |
| Comparison storage | ❌ Blocks the evaluation and score pages — `docs/backlog.md` TD-01 |
| Auth / authorization | ❌ TD-02 |
| Audit log | ❌ TD-03 |
| Frontend | 🔨 Landing page + classroom create · E2E smoke passing |
| Deploy | ❌ Not connected — see `memory-bank/standards/tech-stack.md` |

`pytest` runs 106 tests in about half a second, and the fidelity check catches
11 of 11 deliberately broken rules. What that number does **not** cover is the
ORM layer, which currently has no tests at all — see the coverage table in
[`TEST_PLAN.md`](TEST_PLAN.md).

## The parts worth reading first

- [`backend/app/pairing.py`](backend/app/pairing.py) — feasibility (§8.2) and
  allocation. Coverage and workload derive from each other; when the target
  cannot be met, the engine lowers it and says so in numbers.
- [`backend/app/scoring.py`](backend/app/scoring.py) — the 6-point scale with
  no neutral option, band mapping, and a participation multiplier that is kept
  separate from earned score on purpose.
- [`memory-bank/intent.md`](memory-bank/intent.md) — the eight decisions that
  should not be reopened, and what gets suggested instead each time.
