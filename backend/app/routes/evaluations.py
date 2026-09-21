"""Evaluations endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import schemas
from ..auth import Identity, current_identity
from ..dependencies import get_db
from ..evaluation import read_page, save_draft, submit

router = APIRouter(dependencies=[Depends(current_identity)])


@router.get("/assignments/{assignment_id}/evaluation/{section}")
def evaluation_page(
    assignment_id: int, section: str,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> dict:
    return read_page(db, assignment_id, section, identity.email)


@router.put("/assignments/{assignment_id}/evaluation/{section}/draft")
def update_evaluation_draft(
    assignment_id: int, section: str, payload: schemas.DraftChanges,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> dict:
    return save_draft(db, assignment_id, section, identity.email, [(item.pair_id, item.choice) for item in payload.changes])


@router.post("/assignments/{assignment_id}/evaluation/{section}/submit")
def submit_evaluation(
    assignment_id: int, section: str,
    identity: Identity = Depends(current_identity), db: Session = Depends(get_db),
) -> dict:
    return submit(db, assignment_id, section, identity.email)
