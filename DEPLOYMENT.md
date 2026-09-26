# PairEval on Vercel

Deploy from the repository root. `vercel.json` uses Vercel Services (currently beta) to host the Vite frontend and FastAPI API in one project. `/api/*` goes to FastAPI; the frontend uses this same-origin prefix in production.

A service rewrite forwards the matched path unchanged, so FastAPI receives `/api/...` rather than `/...`. `API_ROOT_PATH` therefore mounts every router under that prefix; without it only `/api/health` resolves and every other endpoint returns 404. Leave `API_ROOT_PATH` unset locally, where the frontend calls the API on its own origin.

## Account and database

1. Run `npx vercel login`, then `npx vercel link` from the repository root.
2. Add Neon PostgreSQL through the project's Vercel Marketplace / Storage integration. Use a separate database or branch for Preview; do not reuse the local or production database for staging.
3. Set these environment variables in Vercel for the intended environment:

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | Neon connection URL, using `postgresql+psycopg://` and retaining `sslmode=require` |
| `API_ROOT_PATH` | `/api` (API service only; mounts the routers under the rewrite prefix) |
| `APP_ENV` | `production` |
| `AUTH_MODE` | `google` |
| `GOOGLE_CLIENT_ID` | Client ID from the Google OAuth client named `pairwise` |
| `VITE_GOOGLE_CLIENT_ID` | The same client ID |
| `FRONTEND_ORIGINS` | The HTTPS staging origin |
| `INSTRUCTOR_EMAILS` | Comma-separated approved instructor emails |
| `ADMIN_EMAILS` | Comma-separated approved administrator emails |
| `VITE_AUTH_MODE` | Leave unset, or `google`. Never `mock` outside local development |

Leave `VITE_API_BASE_URL` unset so the frontend uses `/api`. Vite inlines `VITE_*` values at build time, so `VITE_GOOGLE_CLIENT_ID` must be present for the frontend service in every environment you build, not only at runtime. Environment files are excluded from CLI uploads. Never put a database password or Google client secret in `VITE_*` variables.

## Migration and deployment

Set `DATABASE_URL` in your terminal to the staging database URL, then run `python -m alembic upgrade head` from `backend` using its virtual environment. Migrations are an explicit step; deployment does not automatically mutate the database.

Run `npx vercel` from the repository root for a Preview deployment. Use a stable staging domain when configuring Google OAuth. In Google Cloud Console, add that exact HTTPS origin to `pairwise`'s Authorized JavaScript origins, keeping `http://localhost:5173` for local development. Google Identity Services uses JavaScript origins here, rather than a redirect URI.

Check `/api/health`, Google instructor/student sign-in, classroom creation and CSV import, preview/publication, submission, score visibility and exports on the deployed domain. Local mock-auth E2E checks do not verify live Google authentication or Vercel deployment. Promote with `npx vercel --prod` only when the staging checks pass and production environment/database settings are configured.

References: [Services](https://vercel.com/docs/services), [service configuration](https://vercel.com/docs/services/config-reference), [FastAPI](https://vercel.com/docs/frameworks/backend/fastapi), [PostgreSQL marketplace](https://vercel.com/docs/postgres).
