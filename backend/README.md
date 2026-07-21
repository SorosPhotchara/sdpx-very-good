# PairEval Backend

This folder contains the FastAPI prototype backend for the PairEval system.

## Requirements

- Python 3.11 or 3.13
- `py` launcher on Windows

## Install

```bash
cd backend
py -m pip install -r requirements.txt
```

## Run

```bash
cd backend
bun run dev
```

or directly:

```bash
cd backend
py -m uvicorn app.main:app --reload
```

The backend runs on `http://localhost:8000`.

## Notes

- The SQLite database file is `backend/paireval.db`.
- If `bun run dev` fails because `py` is not found, use `py -m uvicorn app.main:app --reload` directly.
