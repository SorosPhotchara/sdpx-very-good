# PairEval API contract

Base URL: `http://localhost:8000` in local development. FastAPI also serves generated OpenAPI JSON at `/openapi.json` and interactive documentation at `/docs`.

All routes except `GET /health` require `Authorization: Bearer <Google ID token>`. The token's audience must match `GOOGLE_CLIENT_ID` and its email must be verified. Error responses use `{"detail": "..."}` for domain errors and FastAPI's validation detail array for malformed requests. Common statuses: `401` missing/invalid token, `403` insufficient membership, `404` unknown or hidden resource, `409` closed deadline/lifecycle conflict, `422` invalid data or impossible pairing. Numeric IDs are scoped by the path's Classroom or Assignment, never trusted on their own.

| Method and path | Caller | Request / key response |
| --- | --- | --- |
| `GET /health` | public | `{"status":"ok"}` |
| `GET /me` | verified user | Email, instructor flag, classroom membership IDs; activates matching pending Student memberships. |
| `GET /classrooms/?skip=0&limit=100` | member or assigned instructor | Visible Classrooms only. `skip >= 0`, `1 <= limit <= 100`. |
| `POST /classrooms/` | approved instructor | `{name}`; returns Classroom, with caller as first instructor. |
| `PATCH /classrooms/{id}` | assigned instructor | `{name}`; trims and rejects blank names; returns updated Classroom. Membership and evaluations are preserved. |
| `DELETE /classrooms/{id}` | assigned instructor | JSON `{name}` must match the current classroom name (409 otherwise). Returns 204; permanently removes only this classroom and its roster, groups, assignments, evaluations, notifications and reassignment history in one transaction. |
| `POST /classrooms/{id}/instructors` | assigned instructor | `{email}`; email must be in the environment allowlist. |
| `DELETE /classrooms/{id}/instructors/{email}` | assigned instructor | Removes an instructor unless they are the last one. |
| `POST /classrooms/{id}/roster/import` | assigned instructor | `{csv_text}` with header `email,groupname`; returns imported count and row errors. Import is atomic and accepted once per empty roster. |
| `GET /students/?classroom_id=...`, `GET /groups/?classroom_id=...` | assigned instructor | Classroom roster or groups; `skip >= 0`, `1 <= limit <= 500`. |
| `POST /classrooms/{id}/assignments` | assigned instructor | Full AssignmentSetup: title, Group/Individual work and participation maxima, deadlines, criterion lists, instructor weight. |
| `GET /assignments/?classroom_id=...` | member or assigned instructor | Students see published Assignments only; instructors also see drafts. `skip >= 0`, `1 <= limit <= 500`. |
| `GET/PUT /assignments/{id}/setup` | assigned instructor | Read or replace full setup; PUT is closed after publication. |
| `GET /assignments/{id}/criteria` | assigned instructor | Criterion IDs, names, weights, section flags. |
| `GET /assignments/{id}/preview` | assigned instructor | `{pair_assignments}` without persistence. |
| `POST /assignments/{id}/publish` | assigned instructor | `{pair_assignments}`; one publication only. |
| `GET /assignments/{id}/evaluation/{group\|individual}` | assigned student | Only that student's Pair IDs, subject labels, draft/submitted choices, deadline and open state. |
| `PUT /assignments/{id}/evaluation/{section}/draft` | assigned student | `{changes:[{pair_id,choice}]}`; choice 1–5 or null to clear. Changes are atomic. |
| `POST /assignments/{id}/evaluation/{section}/submit` | assigned student | Copies all current draft answers for that section into a new immutable snapshot; returns submitted/assigned counts. |
| `POST /assignments/{id}/instructor-pairs` | assigned instructor | `{criteria_id,left_id,right_id,instructor_email}`; targets an assigned instructor. |
| `GET /assignments/{id}/instructor-pairs` | assigned instructor | Caller’s active targeted pairs and votes. |
| `PUT /assignments/{id}/instructor-pairs/{pair_id}/vote` | assigned instructor evaluator | `{choice:1..5}`; updates their vote before deadline. |
| `GET /assignments/{id}/my-scores` | enrolled student | Only caller's work and participation scores. |
| `GET /assignments/{id}/report` | assigned instructor | All student/group totals, criterion scores, coverage, section final flags. |
| `GET /assignments/{id}/report/{groups\|students\|pairs}.csv` | assigned instructor | CSV sheet with formula-leading text escaped. |
| `GET /assignments/{id}/report.xlsx` | assigned instructor | XLSX with Group Summary, Individual Summary, Raw Pairs. |
| `PUT /classrooms/{id}/students/{student_id}/group` | assigned instructor | `{group_id}`; returns changed Pair and notified Student counts. |
| `GET /classrooms/{id}/reassignments` | assigned instructor | Reassignment audit records, newest first. |
| `GET /classrooms/{id}/notifications` | enrolled student | Caller’s 20 most recent Classroom notifications. |

`group_deadline` and `individual_deadline` are ISO 8601 timestamps with offsets. Submit uses the latest saved drafts for the whole section; sending no choices to the submit endpoint does not erase the previous submission. To replace a previous answer, clear its draft choice and submit again. The response's `submitted_at` and `published_at` are UTC timestamps.

The legacy `POST /students/` and `POST /groups/` instructor routes remain for local setup; the normal roster path is the atomic CSV import. Endpoint response shapes are available in `/openapi.json`.
