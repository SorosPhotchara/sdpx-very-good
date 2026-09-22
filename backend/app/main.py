"""FastAPI application composition."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .dependencies import get_db
from .routes import assignments, classrooms, evaluations, reports

app = FastAPI(title="PairEval Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


for route_group in (classrooms, assignments, evaluations, reports):
    app.include_router(route_group.router)
