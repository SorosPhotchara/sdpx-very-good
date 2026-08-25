# PairEval — Architecture

> Mermaid rather than exported images, so the diagram shows up in `git diff`
> and an AI agent can read it as text. Source of truth for requirements:
> `pairwise_evaluation_prd.md`.

## Component diagram

```mermaid
flowchart TB
    U["Student / Instructor<br/>browser · mobile-first"]

    U -->|"HTTPS · OIDC redirect"| AUTH["Auth Service<br/>Google OAuth 2.0"]
    U -->|"HTTPS"| FE["Frontend<br/>Vite + React + TS"]
    FE -->|"REST / JSON<br/>fetch"| API["API Layer<br/>FastAPI"]
    AUTH -->|"id_token"| API

    API --> AUTHZ["Authorization<br/>role + classroom scope"]
    AUTHZ --> ROSTER["Roster Import<br/>app/roster.py"]
    AUTHZ --> PAIR["Pairing Engine<br/>app/pairing.py"]
    AUTHZ --> SCORE["Scoring Engine<br/>app/scoring.py"]
    AUTHZ --> RPT["Reports & Export"]

    ROSTER --> DB[("Database<br/>SQLite dev · PostgreSQL prod")]
    PAIR --> DB
    SCORE --> DB
    RPT --> DB

    SCORE -.->|"nightly 02:00 + on demand"| JOB["Scheduled Job Runner"]
    JOB --> DB

    API -->|"append-only"| AUDIT[("Audit Log")]
    API --> NOTIF["Notification Service<br/>email"]
```

## What talks to what

| Edge | Protocol | Carries |
|---|---|---|
| Browser → Auth | HTTPS, OIDC redirect | Google consent, `id_token` |
| Browser → Frontend | HTTPS | HTML/JS/CSS |
| Frontend → API | REST/JSON over HTTPS | classrooms, assignments, comparisons |
| API → Authorization | in-process | every request, no exceptions (AR-02) |
| Engines → Database | SQLAlchemy | rows only — the engines hold no state |
| API → Audit log | append-only writes | actor, action, before/after, reason |
| Scheduler → Scoring | in-process | nightly recompute (FR-SCORE-06) |

## Where the rules actually live

The two engines are the parts that must be provably right, so they are pure
functions over dataclasses with no database access at all (AR-01). That is what
lets `backend/tests/property/` throw thousands of random classrooms at the
pairing rules in under two seconds.

| Module | Owns | Spec |
|---|---|---|
| `app/pairing.py` | feasibility, allocation, INV-1 … INV-5 | §8 |
| `app/scoring.py` | 6-point scale, quality index, band mapping, participation | §9 |
| `app/roster.py` | CSV parsing, email normalisation, formula-injection defence | §7.2 |
| `app/services.py` | wiring the engines to storage; publish and score flows | §7.3–7.6 |
| `app/utils.py` | ORM ↔ engine translation only | — |

## Three architectural rules

- **AR-01** — the Scoring Engine is a pure function of what is in the database.
  Recompute must give identical digits, or a mark cannot be defended in an
  appeal (FR-SCORE-10).
- **AR-02** — every read that could reveal *who evaluated whom* goes through
  one authorization layer. Two code paths means one of them will be forgotten.
- **AR-03** — the audit log is append-only and stored separately from
  operational data. A log the application can edit is not evidence.

## Request path for a submitted comparison

```mermaid
sequenceDiagram
    participant S as Student
    participant FE as Frontend
    participant API as API
    participant AZ as Authorization
    participant DB as Database

    S->>FE: pick 1–6 on a pair
    FE->>API: PUT /api/comparisons/{pairAssignmentId}
    Note over FE,API: autosave, debounced ≤ 2s, idempotent (FR-API-01)
    API->>AZ: may this user answer this pair?
    AZ->>DB: pair_assignment.evaluator_id == user?
    AZ-->>API: yes
    API->>DB: upsert comparison (status = DRAFT)
    API-->>FE: 200 { savedAt }
    FE-->>S: "บันทึกแล้ว เมื่อ HH:MM" (aria-live)

    S->>FE: Submit
    FE->>API: POST /api/assignments/{id}/submissions
    API->>DB: status = SUBMITTED + comparison_revision row
    Note over API,DB: every version kept (FR-EVAL-06)
```

## Deployment topology

```mermaid
flowchart LR
    subgraph Vercel
      FEP["frontend/ · static build"]
    end
    subgraph Render
      APIP["backend/ · uvicorn"]
      DBP[("PostgreSQL")]
    end
    GH["GitHub<br/>push to develop"] -->|auto deploy| FEP
    GH -->|auto deploy| APIP
    FEP -->|"VITE_API_BASE_URL"| APIP
    APIP --> DBP
```

Neither side is connected yet — see the Deploy Loop section in
`memory-bank/standards/tech-stack.md` for exactly what is left to do.
