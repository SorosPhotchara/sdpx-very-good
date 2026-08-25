# PairEval Backend

FastAPI service for PairEval. The pairing and scoring engines live here, and
they are the part of the system that has to be provably right.

## Requirements

- Python 3.12 or newer

## Install

```bash
python3 -m pip install -r backend/requirements.txt
```

## Run

From the `backend/` directory:

```bash
python3 -m uvicorn app.main:app --reload
```

Serves on http://localhost:8000 · interactive docs at `/docs` · health check at
`/health`.

> The earlier version of this file used the `py` launcher, which only exists on
> Windows. Use `python3` — every group member has to be able to run this.

## Test

From the **repository root**, not from here:

```bash
pytest                 # every suite
pytest backend/tests   # the engines only
```

## Layout

| Module | Role |
|---|---|
| `app/domain.py` | Dataclasses the engines pass around. Separate from `app/models.py` (the ORM tables) on purpose. |
| `app/pairing.py` | Who compares which pair (PRD §8). Pure functions. |
| `app/scoring.py` | Comparisons → marks (PRD §9). Pure functions, `Decimal` throughout. |
| `app/roster.py` | CSV roster import (PRD §7.2). Atomic. |
| `app/repositories.py` | Storage `Protocol`s, so the test fakes are checked against the real shape. |
| `app/services.py` | Wires the engines to storage. |
| `app/utils.py` | ORM ↔ engine translation only. |
| `app/models.py`, `app/crud.py`, `app/schemas.py` | SQLAlchemy tables, queries and Pydantic schemas. **No test coverage yet.** |

## Notes

- The dev database is `backend/paireval.db` (SQLite). It is git-ignored — it
  used to be committed, which put real rows into version control.
- Production targets PostgreSQL; everything goes through SQLAlchemy so the move
  does not require rewriting queries.
- Marks are `Numeric` in the database and `Decimal` in Python, never `float`
  (DR-04). A grade document that disagrees with itself in the third decimal
  place is a support ticket.
