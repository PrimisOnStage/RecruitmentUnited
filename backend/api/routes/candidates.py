"""Candidate-facing API routes for list, detail, stage updates, and data repair."""

from fastapi import APIRouter, HTTPException, Query

try:
    from backend.database import get_connection
    from backend.models import CandidateStage
    from backend.services.candidate_repository import (
        fill_missing_candidate_values,
        get_candidate_by_id,
        get_candidate_detail,
        list_candidates,
        update_candidate_stage,
    )
    from backend.services.hr_sync import push_candidate_to_hrms
except ImportError:
    import importlib

    get_connection = importlib.import_module("database").get_connection
    CandidateStage = importlib.import_module("models").CandidateStage
    candidate_repository = importlib.import_module("services.candidate_repository")
    fill_missing_candidate_values = candidate_repository.fill_missing_candidate_values
    get_candidate_by_id = candidate_repository.get_candidate_by_id
    get_candidate_detail = candidate_repository.get_candidate_detail
    list_candidates = candidate_repository.list_candidates
    update_candidate_stage = candidate_repository.update_candidate_stage
    push_candidate_to_hrms = importlib.import_module("services.hr_sync").push_candidate_to_hrms


router = APIRouter()


@router.get("/candidates")
def get_candidates_route(
    skill: str | None = None,
    location: str | None = None,
    country: str | None = None,
    min_exp: int | None = Query(default=None, ge=0),
):
    """List candidates with optional exact-skill and partial text filters."""
    return list_candidates(skill=skill, location=location, country=country, min_exp=min_exp)


@router.get("/candidates/{id}")
def get_candidate_route(id: int):
    """Return the full profile view for a single candidate."""
    candidate = get_candidate_detail(id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.patch("/candidates/{id}/stage")
async def update_stage_route(id: int, stage: CandidateStage):
    """Update a candidate's pipeline stage and optionally sync a hire to BambooHR."""
    candidate = get_candidate_by_id(id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    normalized_stage = stage.value
    previous_stage = (candidate.get("stage") or "").strip().lower()
    should_sync_hire = (
        normalized_stage == CandidateStage.HIRED.value
        and previous_stage != CandidateStage.HIRED.value
        and candidate.get("source") != "bamboohr"
    )

    if should_sync_hire:
        await push_candidate_to_hrms(candidate)

    update_candidate_stage(id, normalized_stage)
    return {"status": "updated"}


@router.post("/candidates/fill-missing")
def fill_missing_candidates_route():
    """One-time helper to fill null/blank candidate fields with safe defaults."""
    conn = get_connection()
    try:
        updated = fill_missing_candidate_values(conn)
    finally:
        conn.close()
    return {"status": "success", "updated_rows": updated}

