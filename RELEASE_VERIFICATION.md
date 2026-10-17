# PairEval release verification — 2026-10-17

This records local verification plus the production deployment checks completed for release commit `d61ab2b`.

## Local environment and results

| Check | Result |
| --- | --- |
| Backend, disposable PostgreSQL 17 | `docker compose -f compose.test.yml run --build --rm unit python -m pytest -q`: 66 passed |
| Frontend | `npm.cmd test`: 7 passed; `npm.cmd run lint` and `npm.cmd run build`: passed |
| Chromium workflow | `docker compose -f compose.test.yml run --build --rm e2e`: 27 passed |
| Database migrations | Isolated PostgreSQL upgrade through `20261017_unique_pair_votes` passed; old duplicate pairs were superseded while historical answers remained, and the unique index rejected a new duplicate |
| 200 students, 10 groups | Four runs of `frontend/e2e/scale.spec.ts` passed; classroom switch to visible Group evaluation input: 91–141 ms; maximum of 20 concurrent Individual API reads: 180–221 ms; Publish: 1,626–1,766 ms |
| Pre-deadline load | k6 `performance/load-test.js`: 1→10→0 virtual users over 90 s, mock Student auth, draft writes; 116 iterations, 464/464 checks passed, 0% HTTP and journey errors, HTTP p95 12.03 ms, draft p95 12.89 ms |

The measurements used Docker Desktop Linux engine 28.3.0 on x86_64, exposing 12 CPUs and 7.61 GiB RAM. PostgreSQL data was on disposable tmpfs without a separate container resource cap. Browser measurements used the Playwright Chromium 1.63.0 image and Vite 5.4.21 development server. The browser timer starts at the classroom switch and ends when the first Group evaluation input is visible; it excludes sign-in and initial asset loading. The test services were stopped after verification.

## Access scenarios exercised locally

| Identity | Local evidence |
| --- | --- |
| `teacher@example.edu` | Mock allowlisted Instructor/Admin; classroom setup, report, export, and pair assignment flows |
| `student1@example.edu` | Mock roster Student; evaluation and own score flows |
| Other classroom Instructor | Cannot read another classroom's setup, report, or raw responses |
| Outsider Student | Cannot open a classroom's evaluation |

CSV formula escaping, pseudonymous CSV/XLSX exports, raw-response authorization, and archived deletion are covered by backend and Chromium tests. Exported sample files and real Google account results still need to be attached to the production acceptance record.

## Production checks

On 2026-10-17, release commit `d61ab2b` was pushed to the Vercel production branch `develop`. The production health endpoint at `https://sdpx-very-good.vercel.app/api/health` returned HTTP 200 with `{"status":"ok"}`. The Vercel `DATABASE_URL` was confirmed by the project owners to use the inspected Neon database. Its Alembic revision was verified as `20260925_instructor_approvals`, upgraded with the repository migrations, and verified afterward as `20261017_unique_pair_votes (head)`.

## Outstanding release gates

- Confirm the Vercel deployment detail page identifies `d61ab2b` as the active production deployment.
- Complete Instructor and Student flows with real Google accounts on the production origin, including publication, submission, report export, and denied access.
- Attach the real-account test results, CSV/XLSX samples, known limitations, and product-owner acceptance against the DoD.
