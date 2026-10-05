"""FastAPI application composition."""

import os
import time
from uuid import UUID, uuid4
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from .dependencies import get_db
from .observability import log_event, request_id
from .routes import admin, assignments, classrooms, evaluations, reports

# Behind a platform rewrite such as Vercel's `/api/(.*)`, the upstream path still
# carries the prefix, so the routes must be mounted under it rather than only
# advertised through `root_path`.
API_PREFIX = os.environ.get("API_ROOT_PATH", "").rstrip("/")

app = FastAPI(
    title="PairEval Backend",
    version="0.1.0",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def log_request(request: Request, call_next):
    supplied = request.headers.get("x-request-id", "")
    try:
        correlation_id = str(UUID(supplied))
    except ValueError:
        correlation_id = str(uuid4())
    token = request_id.set(correlation_id)
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["x-request-id"] = correlation_id
        return response
    finally:
        route = request.scope.get("route")
        log_event("http_request", method=request.method, path=getattr(route, "path", "unmatched"),
                  statusCode=status, duration_ms=round((time.perf_counter() - start) * 1000, 2))
        request_id.reset(token)


@app.get("/health")
@app.get("/api/health")
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(status_code=503, detail="Database unavailable") from error
    return {"status": "ok"}


for route_group in (admin, classrooms, assignments, evaluations, reports):
    app.include_router(route_group.router, prefix=API_PREFIX)
