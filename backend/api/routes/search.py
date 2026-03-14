"""Search and indexing API routes backed by PostgreSQL and Pinecone."""

from fastapi import APIRouter

try:
    from backend.database import get_connection
    from backend.processing.vector_store import index_all_existing_candidates, search_candidates
    from backend.services.candidate_repository import fetch_candidates_by_ids, fill_missing_candidate_values
except ImportError:
    import importlib

    get_connection = importlib.import_module("database").get_connection
    vector_store = importlib.import_module("processing.vector_store")
    index_all_existing_candidates = vector_store.index_all_existing_candidates
    search_candidates = vector_store.search_candidates
    candidate_repository = importlib.import_module("services.candidate_repository")
    fetch_candidates_by_ids = candidate_repository.fetch_candidates_by_ids
    fill_missing_candidate_values = candidate_repository.fill_missing_candidate_values


router = APIRouter()


@router.post("/search/index-all")
def index_all_route():
    """Index all existing PostgreSQL candidates into Pinecone."""
    conn = get_connection()
    try:
        updated = fill_missing_candidate_values(conn)
        index_all_existing_candidates(conn)
    finally:
        conn.close()
    return {
        "status": "success",
        "message": "All candidates indexed in Pinecone",
        "filled_missing_rows": updated,
    }


@router.get("/search")
def semantic_search_route(q: str, limit: int = 10):
    """Natural language search using Pinecone plus sentence-transformers."""
    if not q:
        return []

    pinecone_results = search_candidates(q, top_k=limit)
    if not pinecone_results:
        return []

    candidate_ids = [int(result["id"]) for result in pinecone_results]
    scores = {int(result["id"]): result["score"] for result in pinecone_results}
    candidates = fetch_candidates_by_ids(candidate_ids)

    for candidate in candidates:
        candidate["score"] = scores.get(candidate["id"], 0)

    return sorted(candidates, key=lambda item: item["score"], reverse=True)

