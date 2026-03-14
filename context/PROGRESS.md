# Recruitment Platform - Build Progress

## Current Status (2026-03-14)

The repository now contains both a working FastAPI backend and a working Streamlit frontend. Core ingest, browse, profile, compare, pipeline stage updates, and BambooHR sync flows are implemented. The biggest gap is automated testing and hardening for production reliability.

## Current Build Snapshot

### Implemented
- [x] Backend API in `backend/main.py` with routes: `GET /`, `POST /ingest/resume`, `POST /ingest/linkedin`, `POST /ingest/gmail`, `GET /candidates`, `GET /candidates/{id}`, `PATCH /candidates/{id}/stage`, `POST /integrations/bamboohr/push/{id}`, `POST /integrations/bamboohr/sync`
- [x] PostgreSQL bootstrap and schema handling in `backend/database.py` (`init_db`, table creation, compatibility/backfill steps)
- [x] Candidate upsert keyed by unique `email` in `_upsert_candidate` (`backend/main.py`)
- [x] Resume parsing pipeline in `backend/ingest/resume.py`, LinkedIn normalization in `backend/ingest/linkedin.py`, and Gmail candidate ingest in `backend/ingest/gmail.py`
- [x] BambooHR integration logic in `backend/integrations/bamboohr.py`, including pull sync and push helpers
- [x] Frontend recruiter UI in `frontend/app.py` with pages for Candidates, Profile, Compare, Pipeline, and Ingest
- [x] Frontend actions wired to backend endpoints for filtering, stage updates, resume upload, BambooHR sync, and Gmail sync

### Tests Present
- [ ] No automated tests currently present in-repo (`backend/tests/` is not available in the current tree)
- [ ] No API route tests, DB integration tests, or frontend UI tests

### Not Implemented Yet
- [ ] Background job/queue support for long-running sync and ingest operations
- [ ] Authn/authz and role-based access control
- [ ] Strong API input validation for constrained enums (for example candidate stage values)
- [ ] Structured observability (centralized logging/metrics/tracing)

## Known Limitations / Risks

- [ ] `GET /candidates` uses `if min_exp:`, so `min_exp=0` behaves like no filter
- [ ] Skill filtering is exact-match (`%s = ANY(skills)`), which can miss partial or alias-based queries from clients
- [ ] `PATCH /candidates/{id}/stage` verifies candidate existence but does not enforce stage values against a fixed enum
- [ ] Frontend `API_URL` is hardcoded to `http://127.0.0.1:8000` in `frontend/app.py`, which is brittle across environments
- [ ] Frontend request handling is inconsistent: list/profile APIs catch request exceptions, while ingest actions rely on raw status handling without shared retries/backoff
- [ ] Resume, Gmail, and BambooHR flows depend on external credentials/network and currently have no local mocks or test doubles
- [ ] `requirements.txt` is lightweight and largely unpinned, so reproducibility can drift across machines

## Progress Checklist (This Update)

### Completed
- [x] Reconciled progress tracking with actual repository state (frontend exists and is feature-complete for core recruiter workflows)
- [x] Updated API inventory to include Gmail ingest, candidate detail route, and BambooHR push route
- [x] Corrected testing status to reflect that there are currently no in-repo automated tests
- [x] Added frontend-specific operational risks (hardcoded API host and inconsistent request-hardening)

### Next
- [ ] Add backend API tests for ingest routes, filtering, candidate detail, and stage update behavior
- [ ] Add validation for stage transitions/allowed values and return consistent error contracts
- [ ] Externalize frontend API base URL via environment variable or Streamlit secrets
- [ ] Add retry/timeout and partial-failure handling strategy for BambooHR and Gmail synchronization

## Top Priorities

1. Establish baseline automated tests (API + DB integration first).
2. Tighten validation for stage updates and filtering edge cases.
3. Harden external integration reliability (timeouts, retries, partial-failure reporting).
4. Remove environment assumptions from frontend config (`API_URL`).
5. Pin dependencies and document a reproducible local setup.

## Quick Run Reference

```powershell
venv\Scripts\activate
cd backend
python -m uvicorn main:app --reload --port 8000
```

```powershell
venv\Scripts\activate
cd frontend
streamlit run app.py
```

