# Pairwise Engineering Guide

## Product Overview

Pairwise is a student evaluation system for university group work. Instead of giving marks directly, students compare two groups (or two teammates) at a time on each criterion using a 6-point forced choice, and the system turns those comparisons into group and individual scores that the instructor reviews and finalizes. Full requirements are in `docs/prd.md` (PRD v2.0).

The repository is currently an early landing-page scaffold. Login, classrooms, pairing, evaluation, scoring, reports, and persistence are target capabilities, not implemented features. Do not describe them as working until verified in the live code.

## Sources of Truth

Use sources in this order when they disagree:

1. Live code, `package.json`, `bun.lock`, and executable verification.
2. This file for engineering policy and target architecture.
3. `docs/prd.md` for product requirements (requirement IDs such as `FR-EVAL-03`).
4. `memory-bank/standards/tech-stack.md` for approved stack decisions.
5. `README.md` for onboarding; it may lag behind the implementation.

Surface contradictions instead of silently choosing an interpretation. Keep current-state facts separate from planned architecture. Open requirement gaps are tracked in `docs/open-questions.md`.

## Current Repository State

- Frontend only: a Vite single-page app. There is no backend, database, or API yet.
- Runtime: React 19.2 with Vite 7.3 (`@vitejs/plugin-react`).
- Language: TypeScript 5.9 in strict, no-emit mode (`noUnusedLocals`, `noUnusedParameters`, `verbatimModuleSyntax`).
- Entry: `index.html` → `src/main.tsx` (mounts `<App />` in `StrictMode`) → `src/App.tsx` (landing page).
- Styling: Tailwind CSS 4 through `@tailwindcss/vite`; `src/index.css` only imports Tailwind.
- Tooling: Bun is the package manager and test runner; `bun.lock` is the canonical lockfile.
- Tests: `bun:test` in `src/**/*.test.tsx`, rendering components with `renderToStaticMarkup`. There is no DOM testing library and no E2E suite yet.
- Imports: relative paths only; no path alias is configured.
- Available scripts: `dev`, `build`, `preview`, `test`, and `lint`.

## Target Architecture

Decided in `memory-bank/standards/tech-stack.md`, not yet implemented. The component diagram is in `docs/architecture.md`.

- Frontend stays React + TypeScript + Tailwind CSS, deployed on Vercel.
- Backend: FastAPI (Python) with Pydantic validation.
- Database: PostgreSQL, accessed through SQLAlchemy. The schema is in `docs/erd.md`.
- Auth: Google OAuth 2.0 / OIDC authorization code flow run by the server (the browser is redirected through `/api/auth/google/start` and `/api/auth/google/callback`; no Google token reaches JavaScript). Sessions are stored server-side in the `session` table and sent as an `httpOnly`, `Secure`, `SameSite` cookie, so the API must be served from the same site as the SPA (for example a Vercel rewrite of `/api/*`).
- Backend hosting is not decided yet. Do not assume it runs on Vercel.

Install a library only when the task needs it, use its current official integration guidance, and commit the resulting lockfile changes together.

## Project Layout

```text
index.html                 Vite entry point
src/main.tsx               React root
src/App.tsx                Landing page
src/App.test.tsx           Landing page tests
src/components/            Reusable presentation components
src/index.css              Tailwind import
docs/prd.md                Product requirements (PRD v2.0)
docs/architecture.md       Component diagram and architecture decisions
docs/erd.md                ER diagram of the PostgreSQL schema
docs/open-questions.md     Requirement gaps the PRD does not answer yet
docs/user-stories.md       User stories with acceptance criteria (US-CLASS-01, ...)
docs/ui-design.md          UI design guide: brand colors, typography, evaluation UI
memory-bank/standards/     Project standards and stack decisions
memory-bank/units/         Per-unit notes (empty for now)
```

Create new top-level paths (for example a `backend/` directory) only when required by an approved task. Keep feature-specific code together. Do not introduce a generic abstraction until at least two concrete callers need it.

## Development Commands

```bash
bun ci              # install exactly from bun.lock
bun run dev         # Vite dev server on http://localhost:5173
bun test            # run bun:test unit tests
bun run lint        # type-check with tsc --noEmit
bun run build       # type-check, then production build into dist/
bun run preview     # serve the completed production build
```

## Testing

Frontend tests use `bun:test` (built into Bun; no Vitest or Jest).

```bash
bun test                        # run every *.test.tsx once
bun test src/App.test.tsx       # run one file
bun test -t "CTA"               # run tests whose name matches the pattern
bun test --coverage             # print a coverage table in the terminal
bun test --watch                # re-run on every save (interactive)
```

- Put a test file next to the code it covers: `Component.tsx` → `Component.test.tsx`.
- Tests find elements by `data-testid`, never by CSS class or layout.
- A red test means the code is wrong: fix the code, never edit or delete the test to make it pass.

Planned, not set up yet (PRD §18): `pytest` for the FastAPI backend, property-based tests for the pairing invariants (INV-1..5), golden tests from the scoring worked example (§9.5), and Playwright E2E tests in WS-04. Do not document their commands until they exist and run.

## Rules for Agents

- ต้องรัน test ให้เขียวก่อนเสนอ diff เสมอ
- ถ้า test แดง ให้แก้ code — ห้ามแก้หรือลบ test เพื่อให้ผ่าน
- ห้ามใส่ค่า secret ลงไฟล์ใด ๆ ใช้ env var เท่านั้น
- ห้ามแก้ `docs/adr/` และ `memory-bank/` โดยไม่ถามก่อน
- แก้ทีละเรื่อง — diff ที่เกิน ~200 บรรทัดให้หยุดถามก่อน

## Coding Standards

- Persist code, comments, and commit messages in English.
- Preserve strict TypeScript. Avoid `any`; narrow `unknown` at boundaries.
- Use named exports for components (`export function Navbar()`).
- Add `data-testid` to every element a test refers to.
- Use small components and functions with one clear responsibility.
- Match the existing use of double quotes and semicolons.
- Use Tailwind utilities consistently; avoid unrelated global CSS.
- Follow `docs/ui-design.md` for colors, typography, contrast, and evaluation UI patterns.
- Comment why a non-obvious constraint exists, not what readable code already says.
- Do not import or write configuration for a target library before installing it.

## Security and Environment

- Never commit or print secrets, API keys, database URLs, or user data.
- `.gitignore` must ignore `.env` and `.env.*` while explicitly allowing `.env.example`. Verify with `git check-ignore -v .env .env.example` after editing it.
- `.env.example` holds key names only, never values.
- Vite exposes every `VITE_*` variable to the browser bundle. Never put a secret in a `VITE_*` variable.
- Manage deployed configuration with Vercel environment variables, not committed files.

## Verification and Definition of Done

For application changes, the minimum gate is `bun test` and `bun run build`, both green. Also check the changed page through `bun run dev`. For documentation-only changes, run `git diff --check` and verify every command, path, and version against the repository.

A change is complete only when its requested behavior is implemented, relevant edge cases are checked, verification evidence is fresh, no secrets are present, and documentation is updated when interfaces changed. Report missing tooling or unverified behavior plainly.

## Git and Review Workflow

- Work on `feature/*` branches and open a PR into `develop`.
- Preserve unrelated working-tree changes and stage only files belonging to the task.
- Use Conventional Commits: `type(scope): concise summary`. Common types are `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, and `chore`.
- Review every AI-generated change before committing; the contributor must be able to explain it.
- Do not commit, push, deploy, or create a pull request unless the user requests that action.
- Before handoff, review the diff for accidental scope growth and state exactly what was and was not verified.

## Deployment

Vercel hosts the frontend (Vite preset, build command `bun run build`, output `dist`) and deploys automatically on every push to `develop`, which is the Production branch. Staging URL: `https://sdpx-very-good.vercel.app` (also recorded in `memory-bank/standards/tech-stack.md`). Verify the URL and critical flows after every release.
