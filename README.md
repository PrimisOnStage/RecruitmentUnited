# RecruitmentUnited

FastAPI backend for candidate ingestion from resumes and LinkedIn payloads.

## Features
- `POST /ingest/resume` for PDF resume extraction via LlamaCloud.
- `POST /ingest/linkedin` for JSON LinkedIn profile ingestion.
- `GET /candidates` with optional filters.
- `PATCH /candidates/{id}/stage` to update pipeline stage.

## Setup
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```powershell
cd backend
python -m uvicorn main:app --reload --port 8000
```

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

