from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.domain.roster import RosterRow, allocate_pairs, parse_roster

router = APIRouter(prefix="/api/rosters")


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


@router.post("/import", response_model=RosterImportResponse)
def import_roster(payload: RosterImportRequest) -> RosterImportResponse:
    result = parse_roster(payload.csv_text)
    return RosterImportResponse(
        rows=[RosterRowModel(email=row.email, group_name=row.group_name) for row in result.rows],
        errors=result.errors,
    )


@router.post("/preview", response_model=RosterPreviewResponse)
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
