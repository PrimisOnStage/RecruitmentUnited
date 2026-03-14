"""Integration API routes for BambooHR push and pull workflows."""

from fastapi import APIRouter, HTTPException

try:
    from backend.integrations.bamboohr import sync_bamboo_candidates
    from backend.services.candidate_repository import get_candidate_by_id, upsert_candidate
    from backend.services.hr_sync import push_candidate_to_hrms
except ImportError:
    import importlib

    sync_bamboo_candidates = importlib.import_module("integrations.bamboohr").sync_bamboo_candidates
    candidate_repository = importlib.import_module("services.candidate_repository")
    get_candidate_by_id = candidate_repository.get_candidate_by_id
    upsert_candidate = candidate_repository.upsert_candidate
    push_candidate_to_hrms = importlib.import_module("services.hr_sync").push_candidate_to_hrms


router = APIRouter()


@router.post("/integrations/bamboohr/push/{id}")
async def push_candidate_to_bamboohr_route(id: int):
    """Manually push a specific candidate into BambooHR."""
    candidate = get_candidate_by_id(id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    result = await push_candidate_to_hrms(candidate)
    return {"status": "synced", "candidate_id": id, "bamboohr": result}


@router.post("/integrations/bamboohr/sync")
async def bamboo_sync_route():
    """Pull employees from BambooHR and mirror them into the candidate table."""
    await sync_bamboo_candidates(upsert_candidate)
    return {"status": "synced"}

