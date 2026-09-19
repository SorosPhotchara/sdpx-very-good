from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.rosters import router as rosters_router

app = FastAPI(title="Pairwise API")

# The frontend and the API run as separate dev servers (Vite proxies /api to
# here), but the browser still needs this for direct requests, e.g. the
# Swagger "Try it out" page served from this app's own origin on :8000.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(rosters_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
