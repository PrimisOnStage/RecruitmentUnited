# RecruitmentUnited

FastAPI backend for candidate ingestion from resumes and LinkedIn payloads.

## Features
- `POST /ingest/resume` for PDF resume extraction via LlamaCloud.
- `POST /ingest/linkedin` for JSON LinkedIn profile ingestion.
- `POST /ingest/gmail` to pull PDF resume attachments from Gmail.
- `GET /candidates` with optional filters.
- `PATCH /candidates/{id}/stage` to update pipeline stage.

## Setup
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Place Google OAuth client credentials at `backend/credentials.json`.

## Run
```powershell
cd backend
python -m uvicorn main:app --reload --port 8000
```

## Run With Docker
Use Docker Compose from the repository root to run Postgres + API + Streamlit frontend.

```powershell
docker compose up --build
```

- API: `http://localhost:8000`
- Frontend: `http://localhost:8501`

Stop services:

```powershell
docker compose down
```

First-time env setup:

```powershell
Copy-Item .env.example .env
```

Then populate `.env` with valid provider/API credentials before starting.

## Gmail Ingest Notes
- First call to `POST /ingest/gmail` opens a browser for Google OAuth consent.
- After consent, a token is saved to `backend/token.json` and reused for later calls.
- Current Gmail query fetches up to 20 emails matching: `has:attachment filename:pdf`.
- Gmail ingest now uses a resume-likelihood score and skips low-confidence emails.
- Optional env vars:
  - `GMAIL_ATTACHMENT_QUERY` to override Gmail search query.
  - `GMAIL_RESUME_SCORE_THRESHOLD` (default `2.5`) to tune strictness.

## LinkedIn Ingest Example
```json
{
  "name": "Ada Lovelace",
  "email": "ada@example.com",
  "location": "London",
  "current_role": "Research Engineer",
  "experience_years": 6,
  "skills": ["Python", "ML", "ReactJS"],
  "profile_url": "https://www.linkedin.com/in/ada"
}
```

