# Performance Report — WS-07

## Setup and hypothesis

- Date: 5 October 2026; target: **local** FastAPI and PostgreSQL in Docker, with disposable demo data and development-only mock sign-in.
- Load: 0→5 VUs over 30s, 5→10 over 60s, 10→0 over 30s; 1s think time between actions.
- Journey: student identity → assignments → group evaluation page → save the same draft choice. The draft write is enabled only for this disposable local account.
- Hypothesis made before the run: saving a draft will have higher p95 than reading the evaluation page because it commits a row and then reads the page again.

## Results

Full run: 672 requests (5.54/s), 0% failures, overall client p50 6.81 ms and p95 12.36 ms; all thresholds passed, exit code 0. The table uses the 672 matching structured HTTP log events, so these are server durations rather than k6 network durations.

| Route | Count | Server p50 | Server p95 | Errors |
|---|---:|---:|---:|---:|
| `GET /me` | 168 | 2.73 ms | 3.41 ms | 0 |
| `GET /assignments/` | 168 | 4.16 ms | 5.23 ms | 0 |
| `GET /assignments/{assignment_id}/evaluation/{section}` | 168 | 7.07 ms | 8.68 ms | 0 |
| `PUT /assignments/{assignment_id}/evaluation/{section}/draft` | 168 | 10.74 ms | 13.10 ms | 0 |

The hypothesis was supported: draft p95 exceeded evaluation read p95 by 4.42 ms. k6 measured draft p95 14.00 ms and evaluation p95 9.43 ms. Nine of the ten slowest request log lines were draft writes; the slowest was 21.15 ms.

## AI analysis and next measurement

1. Most likely: `save_draft` commits changes and calls `read_page` afterward; both operations occur inside the slower route. Confirm with SQL statement counts and timings around commit and page read.
2. Possible: `read_page` loads drafts, submission choices, criteria and labels with several queries. Confirm with per-query timings before optimizing.
3. Possible: ten VUs share one student and draft pair, causing write contention. Confirm with separate test students and PostgreSQL lock wait metrics.

The evidence supports investigating 1 first. A network bottleneck is not supported by the small client/server p95 gap here. A separate 5s probe with temporary `p(95)<1` failed at 7.98 ms and exited 1; the temporary script was removed. No performance optimization is made on this evidence alone.

## Staging and CI boundary

No load test was sent to `sdpx-very-good.vercel.app`, which appears to be the production domain. The CI job requires a confirmed staging `STAGING_URL` variable and a `PERFORMANCE_BEARER_TOKEN` secret. Google ID tokens expire; a repeatable CI run needs a secure way to issue fresh test credentials.
