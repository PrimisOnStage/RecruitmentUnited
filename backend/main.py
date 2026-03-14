from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import tempfile, json, os, sys
from psycopg2.extras import RealDictCursor
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import get_connection, init_db
from ingest.resume import parse_resume
from ingest.linkedin import parse_linkedin_profile
from models import LinkedInIngestSchema
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="Recruitment Platform API")

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def root():
    return {"status": "Recruitment API running"}


def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def _upsert_candidate(data: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    source_metadata = data.get("source_metadata") or {
        "work_history": data.get("work_history", []),
        "education": data.get("education", []),
    }

    cur.execute("""
        INSERT INTO candidates
            (name, email, phone, country, location, "current_role",
             experience_years, skills, source, raw_text, source_metadata)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (email) DO UPDATE SET
            name=EXCLUDED.name,
            phone=EXCLUDED.phone,
            country=EXCLUDED.country,
            location=EXCLUDED.location,
            "current_role"=EXCLUDED."current_role",
            experience_years=EXCLUDED.experience_years,
            skills=EXCLUDED.skills,
            source=EXCLUDED.source,
            raw_text=EXCLUDED.raw_text,
            source_metadata=EXCLUDED.source_metadata
        RETURNING id
    """, (
        data.get("name"), data.get("email"), data.get("phone"),
        data.get("country"), data.get("location"), data.get("current_role"),
        data.get("experience_years"), data.get("skills"),
        data.get("source"), data.get("raw_text"),
        json.dumps(source_metadata)
    ))
    candidate_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return candidate_id

@app.post("/ingest/resume")
async def ingest_resume(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        data = parse_resume(tmp_path)
    finally:
        os.unlink(tmp_path)
    candidate_id = _upsert_candidate(data)
    return {"status": "success", "candidate_id": candidate_id,
            "name": data.get("name"), "skills": data.get("skills")}


@app.post("/ingest/linkedin")
def ingest_linkedin(payload: LinkedInIngestSchema):
    data = parse_linkedin_profile(payload.model_dump())
    candidate_id = _upsert_candidate(data)
    return {
        "status": "success",
        "candidate_id": candidate_id,
        "source": "linkedin",
        "name": data.get("name"),
        "skills": data.get("skills"),
    }

@app.get("/candidates")
def get_candidates(skill: str = None, location: str = None, country: str = None, min_exp: int = None):
    conn = get_connection()
    cur = conn.cursor()
    query = """SELECT id, name, email, country, location, "current_role",
               experience_years, skills, stage, source
               FROM candidates WHERE 1=1"""
    params = []
    if skill:
        query += " AND %s = ANY(skills)"
        params.append(skill.lower())
    if location:
        query += " AND location ILIKE %s"
        params.append(f"%{location}%")
    if country:
        query += " AND country ILIKE %s"
        params.append(f"%{country}%")
    if min_exp:
        query += " AND experience_years >= %s"
        params.append(min_exp)
    query += " ORDER BY created_at DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id":r[0],"name":r[1],"email":r[2],"country":r[3],"location":r[4],
             "role":r[5],"exp":r[6],"skills":r[7],
             "stage":r[8],"source":r[9]} for r in rows]

@app.patch("/candidates/{id}/stage")
def update_stage(id: int, stage: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE candidates SET stage=%s WHERE id=%s", (stage, id))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "updated"}

