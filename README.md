# PairEval

PairEval is a university pairwise evaluation platform for fair student scoring.

## Overview

This repository contains a Vite + React + TypeScript starter for the PairEval product vision:

- Google OAuth login support for students and instructors
- Classroom import via CSV
- Pairwise group and individual evaluation workflows
- Rolling and final scoring with instructor weighting
- Report export to CSV or Excel
- Anonymous peer evaluation with instructor visibility

## Current status

- `src/App.tsx` contains the landing page for the PairEval product.
- Tailwind CSS is configured for the frontend UI.
- The app is scaffolded for future expansion into authentication, assignment management, pairing, and scoring.

## Run locally

```bash
bun install
bun run dev
```

Open `http://localhost:5173` to view the current landing page.

## Note

The current repository is a UI starter, with the PairEval PRD captured in `pairwise_evaluation_prd.md` for future implementation.
