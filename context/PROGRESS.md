# Recruitment Platform - Build Progress

## Current Status (2026-03-14)

The project has a functional FastAPI backend with PostgreSQL persistence, LinkedIn and resume ingestion paths, and a BambooHR sync endpoint. Local test coverage is currently limited to LinkedIn parsing logic. Frontend work has not started in this repository.

## Current Build Snapshot

### Implemented
- [x] Core API routes in `backend/main.py`: `GET /`, `POST /ingest/resume`, `POST /ingest/linkedin`, `GET /candidates`, `PATCH /candidates/{id}/stage`, `POST /integrations/bamboohr/sync`
- [x] DB bootstrap and schema setup in `backend/database.py` (`init_db`, candidates table creation, optional reset, legacy column backfill)
- [x] Candidate upsert flow keyed by unique `email` in `_upsert_candidate` (`backend/main.py`)
- [x] LinkedIn normalization and skill alias cleanup in `backend/ingest/linkedin.py` and `backend/processing/normaliser.py`
- [x] Resume extraction pipeline via LlamaCloud in `backend/ingest/resume.py`
- [x] BambooHR integration module in `backend/integrations/bamboohr.py` (directory fetch, employee fetch, mapping, sync loop)

### Tests Present
- [x] `backend/tests/test_linkedin_ingest.py` includes 2 unit tests for LinkedIn parsing behavior
- [ ] No API route tests, DB integration tests, resume parser tests, or BambooHR integration tests in-repo

### Not Implemented Yet
- [ ] `frontend/` remains empty (no recruiter dashboard/UI)
- [ ] No background job/queue for long-running sync or ingest operations
- [ ] No authn/authz or role-based access controls

## Known Limitations / Risks

- [ ] `PATCH /candidates/{id}/stage` accepts any stage string and does not return not-found for missing candidate IDs
- [ ] `GET /candidates` uses `if min_exp:`, so `min_exp=0` behaves like no filter
- [ ] Skill filtering is exact-match on normalized values (`%s = ANY(skills)`), which may surprise clients sending raw labels
- [ ] Resume ingest depends on external LlamaCloud credentials and network availability
- [ ] BambooHR sync depends on external BambooHR credentials/network and has no local test harness
- [ ] `requirements.txt` is minimal and unpinned; reproducibility may drift across environments

## Top Priorities

1. Add API + DB integration tests for ingest, list/filter, and stage-update behavior.
2. Tighten validation and response semantics for `PATCH /candidates/{id}/stage`.
3. Fix `min_exp` filtering (`None` vs `0`) and add regression tests.
4. Add dependency pinning and fill runtime gaps required for stable installs.
5. Decide whether BambooHR sync should stay endpoint-triggered or move to a scheduled/background worker.

## Quick Run Reference

```powershell
venv\Scripts\activate
cd backend
python -m uvicorn main:app --reload --port 8000
```
