# PairEval Frontend

Run PostgreSQL with `docker compose up -d postgres` from the repository root, then run the backend and frontend on the host as shown in the root README. Choose the instructor or student demo account at `http://localhost:5173` and switch TH/EN in the top bar.

Run commands from `frontend/`:

```bash
npm ci
npm run dev
npm test
npm run lint
npm run build
```

Vite loads `frontend/.env` automatically and serves the app at `http://localhost:5173`; `.env.example` documents the required variables. Set `VITE_GOOGLE_CLIENT_ID` to the same Google web client ID used by the backend and remove `VITE_AUTH_MODE=mock` to use Google Sign-In. Configure the frontend origin in Google's authorized JavaScript origins. Never put credentials in a `VITE_` variable; Vite includes these values in the browser bundle.

After sign-in, an approved instructor can create a classroom, invite other allowlisted instructors, import its roster, create or edit an assignment, preview and publish pair assignments, add instructor votes, move students between groups before deadlines, and inspect scores and CSV/Excel reports. A student whose verified Google email appears in the roster can save draft choices and submit each evaluation section separately before its deadline. Refresh the score panel after submitting to see the latest calculated results.
