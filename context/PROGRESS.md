# Recruitment Platform - Build Progress

## Current Status (2026-03-14)

The backend is functional for core candidate ingest/list/update flows and includes a working BambooHR sync endpoint. Candidate persistence and upsert behavior are in place via PostgreSQL. Test coverage is still limited to LinkedIn parsing, and frontend work has not started in this repository.

## Current Build Snapshot

### Implemented
- [x] Core API routes in `backend/main.py`: `GET /`, `POST /ingest/resume`, `POST /ingest/linkedin`, `GET /candidates`, `PATCH /candidates/{id}/stage`, `POST /integrations/bamboohr/sync`
- [x] DB bootstrap and schema setup in `backend/database.py` (`init_db`, candidates table creation, optional reset, legacy column backfill)
- [x] Candidate upsert flow keyed by unique `email` in `_upsert_candidate` (`backend/main.py`)
- [x] LinkedIn normalization and skill alias cleanup in `backend/ingest/linkedin.py` and `backend/processing/normaliser.py`
- [x] Resume extraction pipeline via LlamaCloud in `backend/ingest/resume.py`
- [x] BambooHR integration module in `backend/integrations/bamboohr.py` (`get_employees_directory`, `get_employee`, `convert_employee_to_candidate`, `sync_bamboo_candidates`)
- [x] BambooHR endpoint wiring in `backend/main.py` (`POST /integrations/bamboohr/sync` -> `sync_bamboo_candidates(_upsert_candidate)`)

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
- [ ] BambooHR sync currently fetches employee details sequentially; large directories may be slow
- [ ] BambooHR sync raises on first upstream HTTP failure (`raise_for_status`) and does not support partial-success reporting
- [ ] `requirements.txt` is minimal and unpinned; reproducibility may drift across environments

## Progress Checklist (This Update)

### Completed
- [x] Verified BambooHR integration flow is implemented end-to-end (directory fetch -> per-employee fetch -> candidate mapping -> upsert)
- [x] Confirmed BambooHR sync endpoint is exposed in API routes
- [x] Updated progress tracking to separate completed work from remaining hardening tasks

### Next
- [ ] Add BambooHR unit/integration tests (mock `httpx.AsyncClient` and sync endpoint behavior)
- [ ] Add timeout/retry and partial-failure handling for BambooHR sync calls
- [ ] Decide whether BambooHR sync remains request-triggered or moves to scheduled/background execution

## Top Priorities

1. Add API + DB integration tests for ingest, list/filter, stage-update, and BambooHR sync behavior.
2. Tighten validation and response semantics for `PATCH /candidates/{id}/stage`.
3. Fix `min_exp` filtering (`None` vs `0`) and add regression tests.
4. Harden BambooHR sync (timeouts/retries, partial-failure handling, and performance strategy).
5. Add dependency pinning and fill runtime gaps required for stable installs.

## Quick Run Reference

```powershell
venv\Scripts\activate
cd backend
python -m uvicorn main:app --reload --port 8000
```
