# AGENTS.md

## Project

PairEval lets a university grade group work by **pairwise comparison** — students
and instructors answer "is A or B better?" and the system synthesises scores —
so that individual contribution inside a group can be told apart with evidence.

Full requirements: `pairwise_evaluation_prd.md`. Intent and scope:
`memory-bank/intent.md`.

## Setup & Commands

Run everything from the repository root unless noted.

| Purpose | Command |
|---|---|
| install (backend) | `python3 -m pip install -r backend/requirements.txt` |
| install (backend, incl. test tools) | `python3 -m pip install -r backend/requirements-dev.txt` |
| install (frontend) | `cd frontend && npm install` |
| install (e2e browser) | `cd frontend && npx playwright install chromium` |
| **test** | `pytest` |
| test (one suite) | `pytest backend/tests` |
| coverage | `python3 -m coverage run -m pytest && python3 -m coverage html && rm -f docs/coverage/.gitignore` |
| e2e | `cd frontend && npx playwright test` |
| dev (backend) | `cd backend && python3 -m uvicorn app.main:app --reload` |
| dev (frontend) | `cd frontend && npm run dev` |
| build (frontend) | `cd frontend && npm run build` |
| lint (openapi) | `python3 -m openapi_spec_validator docs/openapi.yaml` |

`pytest` runs all three suites at once — see `pytest.ini`. There is no
`npm test`; the frontend currently has no unit tests, only Playwright E2E.

## Layout

```
backend/app/        FastAPI service. domain.py, pairing.py, scoring.py and
                    roster.py are pure functions — keep them that way (AR-01).
backend/tests/      The real PairEval harness: unit + property tests.
frontend/           Vite + React + TypeScript.
frontend/tests/e2e/ Playwright specs.
docs/               architecture, ERD, OpenAPI, backlog, wireframes.
memory-bank/        Intent, unit briefs, standards. Reasons, not commands.
project/            WS-03 booking-service warm-up from the lab handout.
                    Not part of PairEval — do not extend it.
ws-01-before/       FizzBuzz agent-loop exercise.
```

## Conventions

- Python 3.12+ with type hints on every signature; TypeScript `strict`.
- Money and marks are `Decimal`, never `float` (DR-04).
- Give every element a test will reach a `data-testid`.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- Work on `feature/*`, open a PR into `develop`.
- Requirement IDs from the PRD (`FR-PAIR-06`, `INV-3`, `§9.3`) belong in
  docstrings and test names. They are how a reader gets from code to the rule.

## Rules for agents

- Always run `pytest` green before proposing a diff.
- **If a test is red, fix the code — never edit or delete the test to make it
  pass.** If you believe the test itself is wrong, say so and stop.
- Never put a secret in a file. Environment variables only; add the *name* to
  `.env.example`.
- Never commit `__pycache__`, `*.db`, or build output. If one is already
  tracked, `git rm --cached` it and add it to `.gitignore`.
- Do not edit `docs/adr/` or `memory-bank/` without asking first.
- One concern per change. If a diff passes roughly 200 lines, stop and ask.
- Pairing and scoring are specified down to the arithmetic in PRD §8 and §9.
  Read the section before changing either, and cite the ID you are satisfying.
- Never weaken `check_invariants` to make pairing pass. INV-1 … INV-5 are the
  contract; an allocator that cannot meet them is the thing that is wrong.
