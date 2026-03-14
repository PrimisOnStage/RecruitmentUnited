"""Ingestion API routes for resumes, LinkedIn payloads, and Gmail imports."""

import os
import tempfile

from fastapi import APIRouter, File, UploadFile

try:
    from backend.ingest.gmail import fetch_all_gmail_candidates
    from backend.ingest.linkedin import parse_linkedin_profile
    from backend.ingest.resume import parse_resume
    from backend.models import LinkedInIngestSchema
    from backend.processing.vector_store import index_candidate
    from backend.services.candidate_normalization import build_index_metadata, normalize_candidate_payload
    from backend.services.candidate_repository import upsert_candidate, upsert_gmail_candidates
except ImportError:
    import importlib

    ingest_gmail = importlib.import_module("ingest.gmail")
    ingest_linkedin = importlib.import_module("ingest.linkedin")
    ingest_resume = importlib.import_module("ingest.resume")
    fetch_all_gmail_candidates = ingest_gmail.fetch_all_gmail_candidates
    parse_linkedin_profile = ingest_linkedin.parse_linkedin_profile
    parse_resume = ingest_resume.parse_resume
    LinkedInIngestSchema = importlib.import_module("models").LinkedInIngestSchema
    vector_store = importlib.import_module("processing.vector_store")
    index_candidate = vector_store.index_candidate
    candidate_normalization = importlib.import_module("services.candidate_normalization")
    build_index_metadata = candidate_normalization.build_index_metadata
    normalize_candidate_payload = candidate_normalization.normalize_candidate_payload
    candidate_repository = importlib.import_module("services.candidate_repository")
    upsert_candidate = candidate_repository.upsert_candidate
    upsert_gmail_candidates = candidate_repository.upsert_gmail_candidates


router = APIRouter()


@router.post("/ingest/resume")
async def ingest_resume_route(file: UploadFile = File(...)):
    """Accept a resume PDF, parse it, store it, and index it for semantic search."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        data = parse_resume(tmp_path)
    finally:
        os.unlink(tmp_path)

    data = normalize_candidate_payload(data)
    candidate_id = upsert_candidate(data)
    index_candidate(candidate_id=candidate_id, raw_text=data.get("raw_text", ""), metadata=build_index_metadata(data))
    return {
        "status": "success",
        "candidate_id": candidate_id,
        "name": data.get("name"),
        "skills": data.get("skills"),
    }


@router.post("/ingest/linkedin")
def ingest_linkedin_route(payload: LinkedInIngestSchema):
    """Normalize a LinkedIn payload, upsert it, and index it in Pinecone."""
    data = parse_linkedin_profile(payload.model_dump())
    data = normalize_candidate_payload(data)
    candidate_id = upsert_candidate(data)
    index_candidate(candidate_id=candidate_id, raw_text=data.get("raw_text", ""), metadata=build_index_metadata(data))
    return {
        "status": "success",
        "candidate_id": candidate_id,
        "source": "linkedin",
        "name": data.get("name"),
        "skills": data.get("skills"),
    }


@router.post("/ingest/gmail")
def ingest_gmail_route():
    """Fetch Gmail resume attachments, upsert candidates, and index them in bulk."""
    candidates = fetch_all_gmail_candidates()
    inserted, updated, ingested = upsert_gmail_candidates(candidates)

    for candidate_id, data in ingested:
        index_candidate(candidate_id=candidate_id, raw_text=data.get("raw_text", ""), metadata=build_index_metadata(data))

    return {
        "status": "success",
        "inserted": inserted,
        "updated": updated,
        "total": len(candidates),
    }

