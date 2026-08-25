# PairEval — Entity Relationship Diagram

> Follows PRD §11. The tables in `backend/app/models.py` are a prototype subset;
> the gaps are listed at the bottom and tracked in `docs/backlog.md`.

## Diagram

```mermaid
erDiagram
    USER ||--o{ CLASSROOM_MEMBER : "belongs to"
    CLASSROOM ||--o{ CLASSROOM_MEMBER : contains
    CLASSROOM ||--o{ GROUP_ENTITY : contains
    CLASSROOM ||--o{ ASSIGNMENT : contains
    GROUP_ENTITY ||--o{ CLASSROOM_MEMBER : groups
    ASSIGNMENT ||--o{ CRITERION : defines
    ASSIGNMENT ||--o{ PAIR_ASSIGNMENT : generates
    CRITERION ||--o{ PAIR_ASSIGNMENT : scopes
    USER ||--o{ PAIR_ASSIGNMENT : "is assigned"
    PAIR_ASSIGNMENT ||--|| COMPARISON : "answered by"
    COMPARISON ||--o{ COMPARISON_REVISION : "keeps history"
    ASSIGNMENT ||--o{ COMPUTED_SCORE : produces
    ASSIGNMENT ||--o{ SCORE_OVERRIDE : adjusts
    ASSIGNMENT ||--o{ AUDIT_EVENT : records
    ASSIGNMENT ||--o{ APPEAL : receives
    USER ||--o{ APPEAL : files

    USER {
        int id PK
        string email_normalized UK "lowercase, no dots, no +tag"
        string email_raw
        string display_name
        string google_sub UK "nullable until first login"
        string status "PENDING|ACTIVE|DISABLED"
        datetime created_at
        datetime last_login_at
    }

    CLASSROOM {
        int id PK
        string name
        string slug UK
        string timezone
        string allowed_email_domains "text[]"
        string status "ACTIVE|ARCHIVED"
        int created_by FK
    }

    CLASSROOM_MEMBER {
        int id PK
        int classroom_id FK
        int user_id FK
        string role "OWNER|CO_TEACHER|TA|STUDENT"
        int group_id FK "nullable, students only"
        datetime joined_at
    }

    GROUP_ENTITY {
        int id PK
        int classroom_id FK
        string name "unique per classroom"
    }

    ASSIGNMENT {
        int id PK
        int classroom_id FK
        string name
        string slug
        string artifact_url "A5 - what evaluators look at"
        decimal group_max_score
        decimal individual_max_score
        datetime group_deadline_utc
        datetime individual_deadline_utc
        decimal instructor_weight "default 1.0"
        int target_coverage "default 5"
        int max_workload "default 8"
        int min_comparisons "default 3"
        decimal score_floor "default 0.600"
        decimal score_ceiling "default 1.000"
        decimal completion_threshold "default 0.900"
        string scoring_formula_version
        bigint pairing_seed "reproducibility, INV-5"
        string status "DRAFT|PUBLISHED|OPEN|CLOSED|FINALIZED|ARCHIVED"
    }

    CRITERION {
        int id PK
        int assignment_id FK
        string side "GROUP|INDIVIDUAL"
        string name
        decimal weight_pct "sums to 100 per side"
        int display_order
    }

    PAIR_ASSIGNMENT {
        int id PK
        int assignment_id FK
        int criterion_id FK
        string side "GROUP|INDIVIDUAL"
        int item_a_id "group or user, per side"
        int item_b_id
        int evaluator_user_id FK
        int display_left_item_id "FR-PAIR-08, position shown"
        int generation "bumped on regenerate"
        string source "AUTO|INSTRUCTOR_EXTRA|INSTRUCTOR_SELF"
    }

    COMPARISON {
        int id PK
        int pair_assignment_id FK "unique"
        int evaluator_user_id FK
        int choice "1..6, no neutral"
        string status "DRAFT|SUBMITTED|EXCLUDED"
        int time_on_task_ms "QS-05"
        datetime first_seen_at
        datetime submitted_at
        string excluded_reason
    }

    COMPARISON_REVISION {
        int id PK
        int comparison_id FK
        int choice
        string status
        int revision_no
        datetime submitted_at
    }

    COMPUTED_SCORE {
        int id PK
        int assignment_id FK
        int criterion_id FK
        int item_id
        string side
        int comparison_count
        decimal effective_weight_sum
        decimal quality_index
        decimal score_ratio
        decimal weighted_score
        string flags "LOW_CONFIDENCE|OVERRIDDEN"
        boolean is_final
        string formula_version
    }

    SCORE_OVERRIDE {
        int id PK
        int assignment_id FK
        int item_id
        int criterion_id "nullable = whole side"
        decimal original_value
        decimal override_value
        string reason "NOT NULL, FR-SCORE-08"
        int created_by FK
    }

    AUDIT_EVENT {
        int id PK
        int classroom_id FK
        int assignment_id FK
        int actor_user_id FK
        string action
        string resource_type
        string before_json
        string after_json
        string reason
        string ip_address
        datetime occurred_at
    }

    APPEAL {
        int id PK
        int assignment_id FK
        int student_user_id FK
        string message
        string status "OPEN|RESOLVED|REJECTED"
        string resolution
        datetime created_at
    }
```

## Cardinalities worth arguing about

| Relationship | Cardinality | Why |
|---|---|---|
| `PAIR_ASSIGNMENT` → `COMPARISON` | 1 : 1 | One evaluator, one pair, one current answer. History lives in `COMPARISON_REVISION`, so re-submitting (FR-EVAL-06) does not multiply rows in the scored table. |
| `USER` ↔ `CLASSROOM` | N : M via `CLASSROOM_MEMBER` | The same person is a lecturer in one classroom and a student in another (FR-AUTHZ-03). |
| `GROUP_ENTITY` → `CLASSROOM_MEMBER` | 1 : N | Membership carries the group, not the user row, so a student can be regrouped without touching their identity. |
| `ASSIGNMENT` → `COMPUTED_SCORE` | 1 : N | One row per (criterion, item, is_final) so the interim and finalised numbers coexist for audit. |

## Data rules

| ID | Rule |
|---|---|
| DR-01 | Only `comparison.status = SUBMITTED` enters a calculation. |
| DR-02 | A `pair_assignment` with submitted comparisons is never deleted — regeneration bumps `generation` instead. |
| DR-03 | `computed_score` with `is_final = true` is immutable; changes go through `score_override`. |
| DR-04 | Scores are `numeric`, never `float`. |
| DR-05 | Every timestamp is stored UTC and converted only for display. |

## Gap between this diagram and `backend/app/models.py`

The prototype implements `Classroom`, `Group`, `Student`, `Assignment`,
`Criteria` and `Pair`. Still missing:

| Missing | Consequence today |
|---|---|
| `COMPARISON` and `COMPARISON_REVISION` | The scoring engine is fully tested but has nothing to read from in the API — scores cannot be computed end-to-end yet. |
| `AUDIT_EVENT` | FR-AUDIT-01 is unimplemented, and §19 marks it as one of the three items that must not be cut. |
| `email_normalized` on the student table | `app/roster.py` normalises correctly, but the column that would enforce uniqueness does not exist. |
| `numeric` score columns | `Assignment.group_score` is `Float`, which contradicts DR-04. |
| `CLASSROOM_MEMBER` roles | Roles are not modelled at all, so §3's permission matrix cannot be enforced. |

Each of these is an issue in `docs/backlog.md`.
