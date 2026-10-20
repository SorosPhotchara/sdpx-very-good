# PairEval API contract

Base URL: `http://localhost:8000` in local development. FastAPI also serves generated OpenAPI JSON at `/openapi.json` and interactive documentation at `/docs`.

All routes except `GET /health` require `Authorization: Bearer <Google ID token>`. The token's audience must match `GOOGLE_CLIENT_ID` and its email must be verified. Error responses use `{"detail": "..."}` for domain errors and FastAPI's validation detail array for malformed requests. Common statuses: `401` missing/invalid token, `403` insufficient membership, `404` unknown or hidden resource, `409` closed deadline/lifecycle conflict, `422` invalid data or impossible pairing. Numeric IDs are scoped by the path's Classroom or Assignment, never trusted on their own.

| Method and path | Caller | Request / key response |
| --- | --- | --- |
| `GET /health` | public | `{"status":"ok"}` |
| `GET /me` | verified user | Email, instructor flag, classroom membership IDs; activates matching pending Student memberships. |
| `GET /classrooms/?skip=0&limit=100` | member or assigned instructor | Visible Classrooms only. `skip >= 0`, `1 <= limit <= 100`. |
| `POST /classrooms/` | instructor in `INSTRUCTOR_EMAILS` | `{name}`; returns Classroom, with caller as first instructor. |
| `GET /admin/overview` | administrator in `ADMIN_EMAILS` | Classroom, student, and configured instructor counts. |
| `GET /admin/instructors` | administrator in `ADMIN_EMAILS` | Emails from `INSTRUCTOR_EMAILS` only; legacy database approvals are excluded. |
| `POST /admin/instructors`, `DELETE /admin/instructors/{email}` | administrator in `ADMIN_EMAILS` | Return 409; change `INSTRUCTOR_EMAILS` in server configuration to change eligibility. |
| `PATCH /classrooms/{id}` | assigned instructor | `{name}`; trims and rejects blank names; returns updated Classroom. Membership and evaluations are preserved. |
| `DELETE /classrooms/{id}` | assigned instructor | JSON `{name}` must match the current classroom name (409 otherwise). Returns 204; removes active classroom records in one transaction and retains an evaluation/audit snapshot for at least one academic year. |
| `POST /classrooms/{id}/instructors` | assigned instructor | `{email}`; email must be in the environment allowlist. |
| `DELETE /classrooms/{id}/instructors/{email}` | assigned instructor | Removes an instructor unless they are the last one. |
| `POST /classrooms/{id}/roster/import` | assigned instructor | `{csv_text}` with header `email,groupname`; returns imported count and row errors. Import is atomic and accepted once per empty roster before any Assignment is published; a late import returns 409. |
| `GET /students/?classroom_id=...`, `GET /groups/?classroom_id=...` | assigned instructor | Classroom roster or groups; `skip >= 0`, `1 <= limit <= 500`. |
| `DELETE /classrooms/{id}/students/{student_id}` | assigned instructor | JSON `{email}` must match the student’s current email (409 otherwise). Returns 204; refused with 409 once any Assignment in the classroom is published or any Pair row exists. Removal is permanent, deletes that membership’s notifications and group-move audit rows, keeps the emptied group, and revokes classroom access immediately. An emptied roster accepts a fresh CSV import. |
| `POST /classrooms/{id}/assignments` | assigned instructor | Full AssignmentSetup: title, Group/Individual work maxima, derived total maximum, deadlines, criterion lists, instructor weight, and optionally the score band (`score_floor`, `score_ceiling`) and `completion_threshold`. A supplied `total_score` must equal the two work maxima summed. Band and threshold fields may be omitted to keep the assignment's current values. |
| `GET /assignments/?classroom_id=...` | member or assigned instructor | Students see published Assignments only; instructors also see drafts. `skip >= 0`, `1 <= limit <= 500`. |
| `GET/PUT /assignments/{id}/setup` | assigned instructor | Read or replace full setup; PUT is closed after publication. |
| `GET /assignments/{id}/criteria` | assigned instructor | Criterion IDs, names, weights, section flags. |
| `GET /assignments/{id}/preview` | assigned instructor | `{pair_assignments}` without persistence; initial allocations use distinct eligible Students up to five per criterion/subject pair, then top up so every eligible Student has at least one pair per criterion. `assigned_evaluators` may therefore exceed `target_evaluations`. |
| `POST /assignments/{id}/unpublish` | assigned instructor | Returns a published assignment to `DRAFT` so its setup can change. Requires `reason`. Pairs and every answer against them are stored on the lifecycle event and then removed, which is what makes the criteria editable again. |
| `POST /assignments/{id}/finalize` | assigned instructor | Settles both sections and snapshots the formula settings together with the computed report on the lifecycle event. |
| `POST /assignments/{id}/reopen` | assigned instructor | Returns a finalized assignment to `PUBLISHED`. Requires `reason`. |
| `POST /assignments/{id}/recompute` | assigned instructor | Returns a freshly computed report and records that it was asked for. Refused once finalized, which is served from its snapshot. |
| `GET /assignments/{id}/events` | assigned instructor | Lifecycle history, newest first: action, actor, reason, time, and whether a snapshot was stored. |
| `GET /assignments/{id}/feasibility` | assigned instructor | Coverage and workload a publish would use, per side, with the reason when a target had to be reduced. |
| `POST /assignments/{id}/publish` | assigned instructor | `{pair_assignments}`; one publication only. Fewer than five eligible Students for a pair does not by itself block publication. |
| `GET /assignments/{id}/evaluation/{group\|individual}` | assigned student | Only that student's Pair IDs, subject labels, draft/submitted choices, deadline and open state. |
| `PUT /assignments/{id}/evaluation/{section}/draft` | assigned student | `{changes:[{pair_id,choice}]}`; choice 1–5 or null to clear. Changes are atomic. |
| `POST /assignments/{id}/evaluation/{section}/submit` | assigned student | Copies all current draft answers for that section into a new immutable snapshot; returns submitted/assigned counts. |
| `POST /assignments/{id}/instructor-pairs` | assigned instructor | `{criteria_id,left_id,right_id,instructor_email}`; targets an assigned instructor. |
| `POST /assignments/{id}/student-pairs` | assigned instructor | `{criteria_id,left_id,right_id,student_id}`; adds an eligible student evaluator before the section deadline. Group evaluators cannot compare their own group; Individual evaluators must be a third member of the same group. A Student with an active assignment for that criterion/subject pair cannot receive another; superseded history remains for audit. |
| `GET /assignments/{id}/instructor-pairs` | assigned instructor | Caller’s active targeted pairs and votes. |
| `PUT /assignments/{id}/instructor-pairs/{pair_id}/vote` | assigned instructor evaluator | `{choice:1..5}`; updates their vote before deadline. |
| `GET /assignments/{id}/my-scores` | enrolled student | Only caller's work scores, participation ratio and multiplier, and personal total. |
| `GET /assignments/{id}/report` | assigned instructor | All student/group totals, criterion scores, per-criterion pair coverage, section final flags. Each pair/criterion coverage row includes `eligible_evaluators`, `target_evaluations` (the achievable coverage from the feasibility solver, bounded by `eligible_evaluators`), `assigned_evaluators`, `votes` from distinct effective Student submissions, `missing_to_target = max(0, target_evaluations - votes)`, and `shortage_to_target = max(0, target_coverage - target_evaluations)`. Separately, `instructor_votes` counts submitted Instructor answers, `effective_votes` sums Student votes plus Instructor votes weighted by `instructor_weight`, and `left_points`/`right_points` accumulate weighted pairwise points in `left_id`/`right_id` order. Instructor votes do not close Student coverage gaps. |
| `GET /assignments/{id}/report/raw-pairs` | assigned instructor | Current assigned pairs with `criterion_id`, latest submitted choice/time, and actual evaluator email. `criterion_id` identifies assignments for the selected criterion/subject pair. Students cannot access this route. |
| `GET /assignments/{id}/report/{groups\|students\|pairs}.csv` | assigned instructor | CSV sheet with formula-leading text escaped. Raw Pairs CSV uses pseudonymous evaluator labels. |
| `GET /assignments/{id}/report.xlsx` | assigned instructor | XLSX with Group Summary, Individual Summary, Raw Pairs; evaluator labels are pseudonymous. |
| `GET /classrooms/{id}/students/{student_id}/group/preview?group_id=...` | assigned instructor | Read-only impact preview: new and superseded pair counts, latest submissions containing affected answers, and notification count. |
| `PUT /classrooms/{id}/students/{student_id}/group` | assigned instructor | `{group_id}`; preserves eligible pairs and returns new/superseded Pair, affected submission, and notified Student counts. |
| `GET /classrooms/{id}/reassignments` | assigned instructor | Reassignment audit records, newest first. |
| `GET /classrooms/{id}/notifications` | enrolled student | Caller’s 20 most recent Classroom notifications. |

`group_deadline` and `individual_deadline` are ISO 8601 timestamps with offsets. Submit uses the latest saved drafts for the whole section; sending no choices to the submit endpoint does not erase the previous submission. To replace a previous answer, clear its draft choice and submit again. The response's `submitted_at` and `published_at` are UTC timestamps.

Report downloads use a `Content-Disposition` filename of `{classroom}_{assignment}_{type}_{YYYYMMDD}.{ext}`. CSV types are `group_summary`, `individual_summary`, and `raw_pairs`; the three-sheet Excel type is `report`. Unsafe filename characters are replaced, and UTF-8 names use `filename*` with an ASCII fallback.

The legacy `POST /students/` and `POST /groups/` instructor routes remain for local setup; the normal roster path is the atomic CSV import. Endpoint response shapes are available in `/openapi.json`.
