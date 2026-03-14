"""Main FastAPI application for the recruitment platform backend.

This module is intentionally thin: it creates the FastAPI app, initializes the
schema at startup, registers feature routers, and re-exports a few moved helper
functions for backwards compatibility with existing tests and imports.
"""

from contextlib import asynccontextmanager
import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from backend.api.routes.candidates import router as candidates_router
    from backend.api.routes.ingest import router as ingest_router
    from backend.api.routes.integrations import router as integrations_router
    from backend.api.routes.search import router as search_router
    from backend.database import get_connection, init_db
    from backend.services.candidate_normalization import (
        build_filler_raw_text as _build_filler_raw_text,
        normalize_candidate_payload as _normalize_candidate_payload,
    )
    from backend.services.candidate_repository import (
        fill_missing_candidate_values as _fill_missing_candidate_values,
        get_candidate_by_id as _get_candidate_by_id,
        upsert_candidate as _upsert_candidate,
    )
    from backend.services.hr_sync import push_candidate_to_hrms as _push_candidate_to_hrms
except ImportError:
    # Fallback for the local workflow that runs `uvicorn main:app` from inside the
    # `backend` directory instead of importing the package from the repository root.
    from api.routes.candidates import router as candidates_router
    from api.routes.ingest import router as ingest_router
    from api.routes.integrations import router as integrations_router
    from api.routes.search import router as search_router
    from database import get_connection, init_db
    from services.candidate_normalization import (
        build_filler_raw_text as _build_filler_raw_text,
        normalize_candidate_payload as _normalize_candidate_payload,
    )
    from services.candidate_repository import (
        fill_missing_candidate_values as _fill_missing_candidate_values,
        get_candidate_by_id as _get_candidate_by_id,
        upsert_candidate as _upsert_candidate,
    )
    from services.hr_sync import push_candidate_to_hrms as _push_candidate_to_hrms

load_dotenv()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Run one-time application startup work before serving requests."""
    init_db()
    yield


app = FastAPI(title="Recruitment Platform API", lifespan=lifespan)

# CORS is left wide open for local development and the Streamlit frontend.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Register feature routers. Each router owns one area of the API surface.
app.include_router(ingest_router)
app.include_router(candidates_router)
app.include_router(integrations_router)
app.include_router(search_router)


@app.get("/")
def root():
    """Lightweight health endpoint used to verify the API is alive."""
    return {"status": "Recruitment API running"}
