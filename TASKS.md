# PairEval tasks

Implementation tracker based on [the PRD](project-idea/pairwise_evaluation_prd.md) and [the recorded tech stack](memory-bank/standards/teck-stack.md). Checked items have local implementation and focused verification; unchecked items identify remaining work or external setup.

## Decisions confirmed with the product owner

- Use PostgreSQL exclusively. Docker runs only PostgreSQL; FastAPI and Vite run as separate host processes.
- The first usable release includes evaluation, scores, and basic reports.
- Require at least three nonempty groups before publishing an assignment. Every eligible pair gets five assignments before evaluator load is balanced.
- Allow partial submissions before the deadline and use the latest submission for scoring.
- A non-submitter receives zero for their own participation component; this does not erase the evaluated item's votes from other evaluators.
- Use pairwise instructor evaluation in the first release; direct numeric grading is outside that release.
- Allow group reassignment only before the deadline.
- Permit classroom creation only for instructor accounts approved in advance by an administrator.
- Host FastAPI separately from the Vercel frontend. The API host is not chosen yet.
- A student can belong to multiple classrooms. Email uniqueness is per classroom, and the verified Google email activates all matching pending memberships on first login.
- Use five response levels with an equal/tie choice. Left/right points are `1/0`, `.75/.25`, `.5/.5`, `.25/.75`, and `0/1`.
- Cover every eligible pair at least five times before optimizing evaluator load balance. Do not offer individual evaluation to groups with fewer than three members.
- Preserve the four prototype classrooms in PostgreSQL; the old database file is no longer part of the application.
- Choose the API and PostgreSQL hosting provider later; focus on a local runnable system now.
- Set separate Group and Individual deadlines and participation score maxima per assignment. Students in groups with fewer than three members are exempt from an individual participation penalty.
- Treat participation as a separate score component. A new submission replaces the prior submission snapshot for that page; submitting collects the latest saved draft answers for that page.
- Show an interim item without votes as "no data"; only the final calculation may show zero for an unscored item.
- The four migrated classrooms are assigned to the first approved instructor email.

## 0. Resolve product and technical decisions

- [x] D1 — PostgreSQL is the only database. Versioned migrations, runtime, demo seed, and isolated test schemas are verified against PostgreSQL 17.
- [x] D2 — The first release includes evaluation, scoring, and basic reports.
- [x] D3 — Coverage of five evaluations per eligible pair takes priority; balance evaluator load afterward. Require at least three groups, and skip individual evaluation for groups smaller than three.
- [x] D4 — Accept partial submissions before the deadline and score the latest submission.
- [x] D5 — Zero for non-submission applies to the evaluator's own participation component.
- [x] D6 — The first release uses pairwise instructor evaluation only.
- [x] D7 — Group reassignment is allowed only before the deadline.
- [x] D8 — Administrator-approved instructor accounts can create classrooms; pending CSV students activate on first login.
- [x] D9 — FastAPI runs separately from Vercel; choose a provider after local workflows work.

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

## 3. Instructor setup flow

- [ ] Implement Google login, session handling, role checks, and classroom isolation. Google ID token verification, approved-instructor allowlist, role isolation, sign-out, and expiry re-sign-in are implemented; automatic renewal and live Google configuration remain.
- [x] Create and list classrooms; invite and remove allowlisted instructors with access checks and last-instructor protection.
- [x] Import students from CSV (`email`, `groupname`), report row errors, avoid duplicates, create groups, and activate pending memberships on first verified login.
- [x] Create and edit unpublished assignments with separate group and individual criteria, weights totaling 100% per section, score maxima, deadlines, and instructor vote weight.
- [x] Show a pair allocation preview, publish an assignment, and persist the resulting pair assignments atomically. Backend and frontend controls are implemented.

## 4. Student evaluation flow

- [x] Show only the student's classrooms, assignments, eligible pair assignments, and deadline state.
- [x] Build separate responsive group and individual evaluation panels with five-level pair choices, progress, save draft, submit, and explicit confirmation.
- [x] Enforce eligibility, no self-evaluation, deadline, and submission rules in the API as well as the UI.
- [x] Preserve submission history and use only the latest eligible submission for scoring.
- [x] Test atomic draft failures, repeated submissions, expired deadlines, and outsider/peer access.

## 5. Scoring, reports, and instructor follow-up

- [x] Compute group and individual scores from submitted votes, criterion weights, score maxima, instructor vote weight, and separate participation completion ratios.
- [x] Recompute interim scores when requested (more frequently than daily), finalize by deadline state, and show only the caller's scores to students.
- [x] Build instructor summaries and pair coverage report with effective vote counts, criterion totals, and missing coverage.
- [x] Allow instructor pairwise evaluations and targeted extra instructor pair assignments with eligibility checks.
- [x] Reassign groups before deadlines, preserve matching pairs, invalidate superseded responses for scoring, notify affected students, and record an audit trail.
- [x] Export group, individual, and raw-pair reports as CSV and three-sheet XLSX for instructors, with pseudonymous evaluator labels and formula escaping.

## 6. Release verification

- [ ] Cover the full instructor-to-student workflow with API, frontend, and end-to-end tests.
- [ ] Verify authorization, peer anonymity, CSV/spreadsheet safety, score examples, and reassignment history. Backend tests cover all five areas; browser-level confirmation remains.
- [ ] Check the PRD targets with a classroom of 200 students and 10 groups, including evaluation page load and pre-deadline traffic. The benchmark now runs against an isolated PostgreSQL schema; browser rendering and concurrent traffic remain to verify.
- [ ] Deploy the frontend, API, and persistent database according to D1 and D9; verify health, migrations, login, evaluation, and report export in staging.

## Current implementation snapshot

The repository now has a bilingual React/Vite instructor/student workflow and a FastAPI backend with Google token verification, development-only mock sign-in, roster import, assignment publication, draft and submission snapshots, score calculation, reports, instructor votes, group reassignment, audit, notifications, and CSV/XLSX exports. Docker runs only PostgreSQL 17; frontend and backend run separately on the host. PostgreSQL migrations, demo seed, 37 backend tests using isolated schemas, five frontend API tests, TypeScript lint, production build, and HTTP smoke checks are verified. Remaining release work includes live Google configuration, browser end-to-end coverage, concurrent traffic checks, and staging deployment after the host is chosen.
