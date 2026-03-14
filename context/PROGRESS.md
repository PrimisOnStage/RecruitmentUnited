# Recruitment Platform - Build Progress

## Current Status (2026-03-14)

The repository currently contains a working FastAPI backend for candidate ingestion and basic candidate management, backed by PostgreSQL. LinkedIn ingestion and normalization are implemented and lightly unit tested. Resume ingestion is wired through LlamaCloud, but it depends on external credentials/services and is not covered by local tests in this repo. Frontend and HR-system integrations are still scaffolds or documentation only.

## Verified Today

- [x] LinkedIn parser unit tests pass via `python -m unittest discover -s backend\tests -v`
- [x] `backend/tests/test_linkedin_ingest.py` currently provides 2 passing tests
- [ ] No API-level, database integration, or end-to-end tests are present in the repository

## What Is Implemented

### Backend API (`backend/main.py`)
- [x] `GET /` health endpoint
- [x] `POST /ingest/resume` accepts a PDF upload, writes a temp file, parses it, and upserts the candidate
- [x] `POST /ingest/linkedin` accepts a JSON payload, normalizes it, and upserts the candidate
- [x] `GET /candidates` supports optional filters for `skill`, `location`, `country`, and `min_exp`
- [x] `PATCH /candidates/{id}/stage` updates a candidate stage field
- [x] Startup hook initializes the database schema automatically
- [x] CORS middleware is enabled with permissive settings

### Persistence (`backend/database.py` + upsert logic in `backend/main.py`)
- [x] PostgreSQL connection is read from `DATABASE_URL`
- [x] `candidates` table is created automatically on startup
- [x] `pg_trgm` extension is created if available
- [x] Candidate records are upserted by unique `email`
- [x] `source_metadata` is stored as JSONB
- [x] Legacy `candidate_role` data is backfilled into `current_role` when that old column exists
- [x] Optional reset behavior exists through environment flags / CLI invocation in `backend/database.py`

### Ingestion and Normalization
- [x] `backend/ingest/linkedin.py` normalizes LinkedIn payloads into the DB shape
- [x] LinkedIn ingestion lowercases email, maps `headline` to `current_role` when needed, and stores profile metadata
- [x] `backend/processing/normaliser.py` deduplicates and normalizes skills using alias mapping (`reactjs` -> `react`, `ml` -> `machine learning`, etc.)
- [x] `backend/ingest/resume.py` uses LlamaCloud extraction with `CandidateSchema` to parse resumes
- [x] Resume ingestion tags records with `source="resume"`

### Project Scaffolding
- [x] `backend/docker-compose.yml` defines a local PostgreSQL service
- [x] `.env` supports `LLAMA_CLOUD_API_KEY`, `LLAMA_PIPELINE_ID`, and `DATABASE_URL`
- [x] `README.md` documents basic setup and local run commands

## What Is Not Implemented Yet

- [ ] `frontend/` is currently empty; no dashboard or recruiter UI exists in this repository
- [ ] `backend/integrations/` has no implemented integration modules yet
- [ ] BambooHR support is documentation-only in `bamboohr.md`; there is no BambooHR code path in the backend
- [ ] There are no tests for resume ingestion, database initialization, API routes, or stage updates

## Known Limitations / Risks

- [ ] `PATCH /candidates/{id}/stage` does not validate allowed stage values
- [ ] `PATCH /candidates/{id}/stage` always returns success and does not report when no candidate was updated
- [ ] `GET /candidates` uses `if min_exp:` so `min_exp=0` is treated the same as no filter
- [ ] Skill filtering expects already-normalized exact skill values because the query uses `= ANY(skills)`
- [ ] Resume ingestion depends on external LlamaCloud availability and valid credentials, so it is not self-contained for offline/local testing
- [ ] `requirements.txt` is minimal and does not explicitly list a multipart upload dependency, even though the resume endpoint uses `UploadFile`
- [ ] Dependency versions are unpinned, so local environments may drift over time

## Project Snapshot

```text
RecruitmentUnited/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── docker-compose.yml
│   ├── ingest/
│   │   ├── linkedin.py
│   │   └── resume.py
│   ├── integrations/
│   │   └── __init__.py
│   ├── processing/
│   │   └── normaliser.py
│   └── tests/
│       └── test_linkedin_ingest.py
├── context/
│   └── PROGRESS.md
├── bamboohr.md
├── README.md
└── frontend/
```

## Next Recommended Steps

1. Add API and DB integration tests for all existing endpoints, not just LinkedIn normalization.
2. Validate candidate `stage` with an allowed set of values and return a not-found response when the candidate ID does not exist.
3. Fix `min_exp` filtering to distinguish `0` from `None`.
4. Add the missing runtime/package requirements needed for file upload and reproducible installs.
5. Build the frontend MVP on top of `/candidates` and `/candidates/{id}/stage`.
6. Implement the first real integration module if BambooHR syncing/export is still in scope.

## Quick Run Reference

```powershell
venv\Scripts\activate
cd backend
python -m uvicorn main:app --reload --port 8000
```
