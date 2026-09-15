from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.domain.roster import RosterRow, allocate_pairs, parse_roster

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


class RosterRowModel(BaseModel):
    email: str
    group_name: str


class RosterImportRequest(BaseModel):
    csv_text: str


class RosterImportResponse(BaseModel):
    rows: list[RosterRowModel]
    errors: list[str]


class RosterPreviewRequest(BaseModel):
    rows: list[RosterRowModel]


class PairAssignmentModel(BaseModel):
    evaluator_email: str
    left_group: str
    right_group: str


class RosterPreviewResponse(BaseModel):
    assignments: list[PairAssignmentModel]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/rosters/import", response_model=RosterImportResponse)
def import_roster(payload: RosterImportRequest) -> RosterImportResponse:
    result = parse_roster(payload.csv_text)
    return RosterImportResponse(
        rows=[RosterRowModel(email=row.email, group_name=row.group_name) for row in result.rows],
        errors=result.errors,
    )


@app.post("/api/rosters/preview", response_model=RosterPreviewResponse)
def preview_roster(payload: RosterPreviewRequest) -> RosterPreviewResponse:
    rows = [RosterRow(email=row.email, group_name=row.group_name) for row in payload.rows]
    assignments = allocate_pairs(rows)
    return RosterPreviewResponse(
        assignments=[
            PairAssignmentModel(
                evaluator_email=assignment.evaluator_email,
                left_group=assignment.left_group,
                right_group=assignment.right_group,
            )
            for assignment in assignments
        ]
    )
