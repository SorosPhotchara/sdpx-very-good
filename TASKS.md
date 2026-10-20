# PairEval tasks

Implementation tracker governed by [the Definition of Done](project-idea/DEFINITION_OF_DONE.md), with [the PRD](project-idea/pairwise_evaluation_prd.md) and [the recorded tech stack](memory-bank/standards/tech-stack.md) as supporting context. Checked items indicate local implementation or a settled decision, not release acceptance; the DoD still requires evidence for every applicable checklist item.

## Decisions confirmed with the product owner

- Use PostgreSQL exclusively. Docker runs only PostgreSQL; FastAPI and Vite run as separate host processes.
- The first usable release includes evaluation, scores, and basic reports.
- Require at least three nonempty groups before publishing an assignment. Coverage comes from the feasibility solver: up to the assignment's target for Group pairs, and `m - 2` (complete enumeration) for Individual pairs, each bounded by its workload ceiling. Then even out workloads. Publication is allowed when the target cannot be reached, and the shortfall is reported with its cause. **Supersedes** the earlier `min(5, distinct eligible Student evaluators)` rule (PRD §8.2, §8.3, D4).
- Allow partial submissions before the deadline and use the latest submission for scoring.
- A non-submitter keeps a participation multiplier of zero, which zeroes their own personal score; this does not erase the evaluated item's votes from other evaluators, nor their group's work score.
- Use pairwise instructor evaluation in the first release; direct numeric grading is outside that release.
- Allow group reassignment only before the deadline.
- Permit instructor access only for verified emails in `INSTRUCTOR_EMAILS`, including classroom creation and instructor invitations.
- Host the frontend and FastAPI API together using Vercel Services, with Neon PostgreSQL through the Vercel Marketplace (confirmed by the owner).
- A student can belong to multiple classrooms. Email uniqueness is per classroom, and the verified Google email activates all matching pending memberships on first login.
- Use six response levels with no tie. Left/right points are `1/0`, `.8/.2`, `.6/.4`, `.4/.6`, `.2/.8`, and `0/1`. Each comparison is shown in a randomised left-right order that is stored with it. **Supersedes** the earlier five-level scale with an equal choice (PRD D1, D8).
- Count each Student at most once among active assignments and effective votes for a criterion/subject pair, including after re-submission; keep superseded history for audit. Track distinct submitted Student votes separately from assignments and Instructor votes; show achievable coverage and the shortage from five. Do not offer individual evaluation to groups with fewer than three members.
- Preserve the four prototype classrooms in PostgreSQL; the old database file is no longer part of the application.
- Use Vercel for deployment; account login, Neon provisioning and the staging Google OAuth origin remain external setup.
- Set separate Group and Individual deadlines per assignment. There are no participation score maxima: participation is a multiplier. Students in groups with fewer than three members have no Individual section to answer for.
- Treat participation as a multiplier on the personal score, `min(1, (submitted / assigned) / completion_threshold)` across both sections, not as a score component of its own. **Supersedes** the earlier separate-component decision (PRD D5, §9.4). A new submission replaces the prior submission snapshot for that page; submitting collects the latest saved draft answers for that page.
- Show an interim item without votes as "no data"; only the final calculation may show zero for an unscored item.
- The four migrated classrooms must be assigned to the first instructor email in `INSTRUCTOR_EMAILS`; database-only approvals do not satisfy the DoD.

## 0. Resolve product and technical decisions

- [x] D1 — PostgreSQL is the only database. Versioned migrations, runtime, demo seed, and isolated test schemas are verified against PostgreSQL 17.
- [x] D2 — The first release includes evaluation, scoring, and basic reports.
- [x] D3 — Coverage is solved per side from the assignment's target and workload ceilings, with at most one active assignment per Student. Allow publication when the target cannot be reached; require at least three nonempty groups and skip individual evaluation for groups smaller than three.
- [x] D4 — Accept partial submissions before the deadline and score the latest submission.
- [x] D5 — Non-submission zeroes the evaluator's own participation multiplier, and so their personal score, leaving their group's work score untouched.
- [x] D6 — The first release uses pairwise instructor evaluation only.
- [x] D7 — Group reassignment is allowed only before the deadline.
- [x] D8 — `INSTRUCTOR_EMAILS` is the instructor allowlist; pending CSV students activate on first verified Google login.
- [x] D9 — Vercel Services hosts frontend and API; Neon provides persistent PostgreSQL through the marketplace. Deployment configuration is prepared.

## 1. Establish a reliable development baseline

- [x] Make documented install, dev, test, lint, and build commands match the actual `frontend/` and `backend/` packages; add a repeatable backend test command. Frontend and backend READMEs and focused tests are in place; backend has no separate build step.
- [x] Add meaningful tests for classroom creation/listing, invalid input, publication visibility, membership activation, and cross-classroom access.
- [x] Add versioned PostgreSQL migrations and a clean setup path for D1. Database tests create and remove an isolated PostgreSQL schema per test.
- [x] Document environment variable names and local startup without committing credentials in the backend/frontend READMEs and `.env.example` files.

## 2. Define the domain and API contract

- [x] Model classroom membership, instructors, groups, assignments, criteria, pair assignments, submissions, scores, and reassignment history; document ownership and lifecycle states in backend/DOMAIN.md.
- [x] Specify API requests, responses, errors, pagination, and authorization for each instructor and student flow in `backend/API.md` and `/openapi.json`; keep frontend types aligned with the API.
- [x] Define score calculation with worked Group, Individual, instructor-weight, tie, partial-credit, and missing-vote examples in `backend/DOMAIN.md`; test the calculation and integration.
- [x] Define seeded pairing fixtures for normal, small, impossible, and 200-student classrooms; test persistence through the publish API.
- [x] Resolve the small-pool rule: each eligible Student contributes at most one effective answer to a criterion/subject pair. A three-student group or three one-student groups can therefore start with one assigned evaluator per eligible pair. DoD and PRD specify achievable coverage and a visible shortage from five.
- [x] Verify publish, preview, manual extra assignments, reassignment, and reports use the same unique-evaluator rule; report `eligible_evaluators`, `target_evaluations`, `assigned_evaluators`, `votes`, `missing_to_target`, `shortage_to_target`, `instructor_votes`, `effective_votes`, `left_points`, and `right_points` with Student coverage and weighted Instructor contributions distinct. Raw pair responses include `criterion_id` for filtering assigned evaluators. PostgreSQL tests also cover legacy cleanup and database uniqueness indexes.

## 3. Instructor setup flow

- [ ] Implement Google login, session handling, role checks, and classroom isolation. Token verification, role isolation, expiry, renewal prompts, account continuity and sign-out cancellation are implemented. Google SDK lifecycle is browser-tested; live Google authentication on the deployed origin remains unverified.
- [x] Create and list classrooms; invite and remove allowlisted instructors with access checks and last-instructor protection.
- [x] Enforce the DoD's `INSTRUCTOR_EMAILS` allowlist for every Instructor role check, classroom creation, and invitation. Database approvals no longer grant access; the admin list is read-only. The new migration and development seed add the first allowlisted instructor to existing prototype classrooms.
- [x] Allow assigned instructors to rename and delete a classroom with typed-name confirmation; current deletion removes its roster, assignments, evaluations, and history atomically.
- [x] Retain an evaluation and audit snapshot for at least 366 days when deleting a classroom, in the same transaction as active-record removal. PostgreSQL integration and Alembic upgrade tests pass.
- [x] Import students from CSV (`email`, `groupname`), report row errors, avoid duplicates, create groups, and activate pending memberships on first verified login.
- [x] Create and edit unpublished assignments with separate group and individual criteria, weights totaling 100% per section, score maxima, deadlines, and instructor vote weight.
- [x] Show and validate the derived Assignment total maximum as Group work + Individual work in the API and setup UI.
- [x] Show a pair allocation preview, publish an assignment, and persist the resulting pair assignments atomically. Backend and frontend controls are implemented.

## 4. Student evaluation flow

- [x] Show only the student's classrooms, assignments, eligible pair assignments, and deadline state.
- [x] Build separate responsive group and individual evaluation panels with five-level pair choices, progress, save draft, submit, and explicit confirmation.
- [x] Enforce eligibility, no self-evaluation, deadline, and submission rules in the API as well as the UI.
- [x] Preserve submission history and use only the latest eligible submission for scoring.
- [x] Test atomic draft failures, repeated submissions, expired deadlines, and outsider/peer access.
- [x] Let students choose continuously while autosave is pending. Serialize and batch the latest choices, preserve newer edits when responses arrive, retain failed choices for retry, and block submission until all changes are saved. Browser tests cover delayed writes, multiple pairs, repeated changes and recovery after failure.

## 5. Scoring, reports, and instructor follow-up

- [x] Compute group and individual work scores from submitted votes, criterion weights, score maxima, instructor vote weight and the assignment's score band. Scale a partial submitter's personal total by their participation multiplier, leaving their group's work score and every other student's score untouched.
- [x] Recompute interim scores when requested (more frequently than daily), finalize by deadline state, and show only the caller's scores to students.
- [x] Build instructor summaries and pair coverage report with criterion totals, achievable Student coverage, actual Instructor vote count, weighted effective vote count, and cumulative weighted points for both subjects.
- [x] Verify submitted Student coverage against the achievable target per Group and Individual pair/criterion. When fewer than five distinct students are eligible, expose the fixed shortage from five; when eligible students have not submitted, show the remaining gap to the achievable target and assign unused eligible students before the deadline where possible. API tests cover shortages and duplicate rejection; the Instructor picker hides already assigned evaluators.
- [x] Allow instructor pairwise evaluations and targeted extra instructor pair assignments with eligibility checks.
- [x] Let an Instructor assign extra eligible Group or Individual pairs to Student evaluators before the section deadline, without self-evaluation or cross-group Individual pairs. The UI lists eligible students and submitted-coverage gaps.
- [x] Show a generic confirmation before group reassignment; permit moves only before applicable deadlines, preserve valid pairs, exclude superseded submissions from scoring without deleting history, notify affected students, and record actor, time, old group, and new group.
- [x] Before reassignment, preview counts of superseded and new pairs plus affected submitted snapshots; show the impact before confirmation without changing stored data.
- [x] Export Group Summary, Individual Summary, and Raw Pairs as CSV and a three-sheet XLSX for authorized instructors, with pseudonymous evaluator labels and formula escaping.
- [x] Let an authorized Instructor inspect each current raw pair response and evaluator identity in the report UI/API; Students cannot access it, and exports keep pseudonymous evaluator labels.
- [x] Name each CSV/XLSX export `{classroom}_{assignment}_{type}_{YYYYMMDD}.{ext}` via the API response and frontend download.

## 6. Release verification

- [x] Use Sonner 2.0.8 for toast rendering, SVG status icons, entrance/exit motion, timing and swipe dismissal. Apply distinct success/error/info surfaces, a 36 px close target and mobile safe-area gutters; verify the library markup, icons and drag-to-dismiss behavior in Chromium.
- [x] Replace action feedback with accessible, dismissible toast notifications for assignment creation/editing/publication, student and instructor evaluations, classroom management, roster import, student/group changes, instructor approvals and export failures. Success notices expire after seven seconds, pause during hover/focus, and errors stay until dismissed. Verify repeated messages, keyboard dismissal, reduced motion and mobile viewport gutters.
- [x] Implement and verify responsive design for phone, tablet and desktop layouts at 320, 390, 768, 1024 and 1440 px in Thai and English. The refined layout uses compact mobile room navigation with on-demand classroom creation, consistent card surfaces, fluid spacing and container-based assignment fields. Chromium E2E checks sign-in, instructor forms and classroom tools, student evaluation and scores without page-wide horizontal overflow; additional resize checks cover long classroom names and intermediate widths from 280 to 2560 px. Report tables scroll within keyboard-focusable regions; confirmation dialogs fit narrow and short landscape viewports and respect reduced motion. Screenshots reviewed at 390, 768 and 1440 px. Physical devices and other browser engines have not been tested.
- [x] Cover the full instructor-to-student workflow with API, frontend, and end-to-end tests, including publication, partial submission, scores, exports, reassignment, loading, retries and duplicate-action guards.
- [x] Verify authorization, peer anonymity, CSV/spreadsheet safety, score examples, and reassignment history. Backend tests cover all five areas; browser E2E confirms forbidden report/outsider access, pseudonymous CSV evaluator labels, unsafe roster rejection, escaped CSV exports, and the displayed reassignment history.
- [x] Record an Evaluation page load under two seconds with 200 students and 10 groups in a stated test environment. `frontend/e2e/scale.spec.ts` passed four Chromium runs on 2026-10-17: classroom switch to visible Group evaluation input 91–141 ms; 20 concurrent Individual evaluation API reads had a maximum of 180–221 ms. Docker Desktop Linux engine exposed 12 CPUs and 7.61 GiB RAM; PostgreSQL 17 used a disposable tmpfs, mock auth, and Vite development server. This does not measure deployed staging or initial sign-in/assets.
- [x] Verify Publish and pair creation for the target data set without timeout; run a pre-deadline load test and record concurrency plus test-machine limits. Four 200-student/10-group publishes took 1,626–1,766 ms; a local k6 run on 2026-10-17 ramped 1→10→0 VUs over 90 seconds with mock Student auth and draft writes: 116 completed iterations, 464/464 checks passed, 0% HTTP and journey errors, HTTP p95 12.03 ms, draft p95 12.89 ms. Docker Desktop exposed 12 CPUs and 7.61 GiB RAM; PostgreSQL 17 data was in tmpfs with no separate container limit.
- [ ] Deploy the frontend, API, and persistent database according to D1 and D9; verify health, migrations, login, evaluation, and report export. Release commit `d61ab2b` was pushed to the Vercel production branch `develop`; the production health endpoint returned HTTP 200, and the owner-confirmed Neon database was upgraded from `20260925_instructor_approvals` through `20261017_unique_pair_votes (head)`. The active Vercel deployment revision and live Google workflows remain to be verified.
- [x] Verify release README, `.env.example`, API and domain documentation against the delivered behavior, and close all Critical and High severity defects. The README and guide now describe the strict `INSTRUCTOR_EMAILS` allowlist, archived classroom deletion, and roster cutoff after publication; the focused code audit found no remaining known Critical or High defect.
- [ ] Run critical Instructor and Student flows with real Google Login; attach the release revision, dated test results, load-test setup, account matrix, CSV/XLSX samples, known limitations, and product-owner acceptance against every in-scope DoD item.

## Current implementation snapshot

The bilingual React/Vite and FastAPI workflows include loading/error states, action locks, lazy panels, stale-response protection, Google renewal prompts, responsive controls and action toasts. On 2026-10-17, the rebuilt current worktree passed 66 backend tests against disposable PostgreSQL, 7 frontend API tests, TypeScript lint and production build, and 27 Chromium E2E tests. PostgreSQL migration tests upgraded an isolated schema through `20261017_unique_pair_votes`, preserved historical answers while superseding duplicate active pairs, and verified the uniqueness constraint. The 200-student/10-group browser and publish measurements and the 10-VU k6 result are recorded above and in [RELEASE_VERIFICATION.md](RELEASE_VERIFICATION.md). Release commit `d61ab2b` was pushed to the Vercel production branch `develop`; production health returned HTTP 200 and the confirmed Neon production database was upgraded to `20261017_unique_pair_votes (head)`. The active Vercel deployment revision, live Google authentication and product-owner acceptance remain unverified.
