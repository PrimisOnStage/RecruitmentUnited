from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import tempfile, json, os, sys
from psycopg2.extras import RealDictCursor
import httpx
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import get_connection, init_db
from ingest.resume import parse_resume
from ingest.linkedin import parse_linkedin_profile
from ingest.gmail import fetch_all_gmail_candidates
from models import LinkedInIngestSchema
from dotenv import load_dotenv
from integrations.bamboohr import create_employee, employee_exists_by_email, sync_bamboo_candidates
from processing.vector_store import index_candidate, search_candidates, index_all_existing_candidates

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


def _build_filler_raw_text(data: dict) -> str:
    skills = data.get("skills") or []
    skills_text = ", ".join([str(skill).strip() for skill in skills if str(skill).strip()])
    parts = [
        f"Name: {data.get('name') or 'Unknown Candidate'}",
        f"Role: {data.get('current_role') or 'Unknown Role'}",
        f"Location: {data.get('location') or 'Unknown Location'}",
        f"Country: {data.get('country') or 'Unknown Country'}",
        f"Experience: {data.get('experience_years') or 0} years",
        f"Skills: {skills_text or 'general'}",
        f"Source: {data.get('source') or 'unknown'}",
    ]
    return ". ".join(parts)


def _normalize_candidate_payload(data: dict) -> dict:
    payload = dict(data or {})

    def _clean_text(value, default=""):
        if value is None:
            return default
        value = str(value).strip()
        return value or default

    raw_skills = payload.get("skills") or []
    if isinstance(raw_skills, str):
        raw_skills = [part.strip() for part in raw_skills.split(",") if part.strip()]
    skills = [str(skill).strip() for skill in raw_skills if skill is not None and str(skill).strip()]

    try:
        experience_years = int(payload.get("experience_years") or 0)
    except (TypeError, ValueError):
        experience_years = 0

    normalized = {
        "name": _clean_text(payload.get("name"), "Unknown Candidate"),
        "email": _clean_text(payload.get("email")),
        "phone": _clean_text(payload.get("phone")),
        "country": _clean_text(payload.get("country"), "Unknown Country"),
        "location": _clean_text(payload.get("location"), "Unknown Location"),
        "current_role": _clean_text(payload.get("current_role"), "Unknown Role"),
        "experience_years": max(0, experience_years),
        "skills": skills or ["general"],
        "source": _clean_text(payload.get("source"), "unknown"),
        "raw_text": _clean_text(payload.get("raw_text")),
        "source_metadata": payload.get("source_metadata") or {
            "work_history": payload.get("work_history", []),
            "education": payload.get("education", []),
        },
    }

    if not normalized["raw_text"]:
        normalized["raw_text"] = _build_filler_raw_text(normalized)

    return normalized


def _fill_missing_candidate_values(conn) -> int:
    """Backfill nullable fields with safe filler values so all rows are indexable."""
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE candidates
        SET
            name = COALESCE(NULLIF(BTRIM(name), ''), 'Unknown Candidate'),
            phone = COALESCE(NULLIF(BTRIM(phone), ''), ''),
            country = COALESCE(NULLIF(BTRIM(country), ''), 'Unknown Country'),
            location = COALESCE(NULLIF(BTRIM(location), ''), 'Unknown Location'),
            "current_role" = COALESCE(NULLIF(BTRIM("current_role"), ''), 'Unknown Role'),
            experience_years = COALESCE(experience_years, 0),
            skills = COALESCE(skills, ARRAY['general']::text[]),
            source = COALESCE(NULLIF(BTRIM(source), ''), 'unknown'),
            raw_text = COALESCE(
                NULLIF(BTRIM(raw_text), ''),
                CONCAT_WS(
                    '. ',
                    'Name: ' || COALESCE(NULLIF(BTRIM(name), ''), 'Unknown Candidate'),
                    'Role: ' || COALESCE(NULLIF(BTRIM("current_role"), ''), 'Unknown Role'),
                    'Location: ' || COALESCE(NULLIF(BTRIM(location), ''), 'Unknown Location'),
                    'Country: ' || COALESCE(NULLIF(BTRIM(country), ''), 'Unknown Country'),
                    'Experience: ' || COALESCE(experience_years::text, '0') || ' years',
                    'Skills: ' || COALESCE(NULLIF(array_to_string(skills, ', '), ''), 'general'),
                    'Source: ' || COALESCE(NULLIF(BTRIM(source), ''), 'unknown')
                )
            )
        WHERE
            name IS NULL OR BTRIM(name) = '' OR
            phone IS NULL OR
            country IS NULL OR BTRIM(country) = '' OR
            location IS NULL OR BTRIM(location) = '' OR
            "current_role" IS NULL OR BTRIM("current_role") = '' OR
            experience_years IS NULL OR
            skills IS NULL OR
            source IS NULL OR BTRIM(source) = '' OR
            raw_text IS NULL OR BTRIM(raw_text) = ''
        """
    )
    updated_rows = cur.rowcount
    cur.close()
    conn.commit()
    return updated_rows


def _upsert_candidate(data: dict) -> int:
    data = _normalize_candidate_payload(data)
    conn = get_connection()
    cur = conn.cursor()
    source_metadata = data.get("source_metadata") or {}

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


def _get_candidate_by_id(candidate_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        'SELECT id, name, email, source, stage, "current_role" FROM candidates WHERE id=%s',
        (candidate_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


async def _push_candidate_to_hrms(candidate: dict):
    email = candidate.get("email")
    if not email:
        raise HTTPException(status_code=422, detail="Candidate email is required for HRMS sync")

    if candidate.get("source") == "bamboohr":
        raise HTTPException(status_code=409, detail="Candidate originated from BambooHR")

    try:
        if await employee_exists_by_email(email):
            raise HTTPException(status_code=409, detail="Employee already exists in BambooHR")
        return await create_employee(candidate)
    except HTTPException:
        raise
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=f"BambooHR sync failed: {exc}") from exc

@app.post("/ingest/resume")
async def ingest_resume(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        data = parse_resume(tmp_path)
    finally:
        os.unlink(tmp_path)
    data = _normalize_candidate_payload(data)
    candidate_id = _upsert_candidate(data)
    index_candidate(
        candidate_id=candidate_id,
        raw_text=data.get("raw_text", ""),
        metadata={
            "name":           data.get("name"),
            "location":       data.get("location"),
            "candidate_role": data.get("current_role"),
            "skills":         data.get("skills", []),
            "source":         data.get("source"),
        }
    )
    return {"status": "success", "candidate_id": candidate_id,
            "name": data.get("name"), "skills": data.get("skills")}


@app.post("/ingest/linkedin")
def ingest_linkedin(payload: LinkedInIngestSchema):
    data = parse_linkedin_profile(payload.model_dump())
    data = _normalize_candidate_payload(data)
    candidate_id = _upsert_candidate(data)
    index_candidate(
        candidate_id=candidate_id,
        raw_text=data.get("raw_text", ""),
        metadata={
            "name":           data.get("name"),
            "location":       data.get("location"),
            "candidate_role": data.get("current_role"),
            "skills":         data.get("skills", []),
            "source":         data.get("source"),
        }
    )
    return {
        "status": "success",
        "candidate_id": candidate_id,
        "source": "linkedin",
        "name": data.get("name"),
        "skills": data.get("skills"),
    }


@app.post("/ingest/gmail")
def ingest_gmail():
    candidates = fetch_all_gmail_candidates()

    inserted = 0
    updated = 0

    conn = get_connection()
    cur = conn.cursor()

    ingested = []   # collect (candidate_id, data) for Pinecone indexing after commit

    for data in candidates:
        data = _normalize_candidate_payload(data)
        if not data.get("email"):
            continue

        source_metadata = data.get("source_metadata") or {}
        cur.execute(
            """
            INSERT INTO candidates
                (name, email, phone, country, location, "current_role",
                 experience_years, skills, source, raw_text, source_metadata)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (email) DO UPDATE SET
                skills = EXCLUDED.skills,
                raw_text = EXCLUDED.raw_text,
                source_metadata = candidates.source_metadata || EXCLUDED.source_metadata
            RETURNING id, (xmax = 0) AS is_insert
        """,
            (
                data.get("name"),
                data.get("email"),
                data.get("phone"),
                data.get("country"),
                data.get("location"),
                data.get("current_role"),
                data.get("experience_years"),
                data.get("skills"),
                data.get("source"),
                data.get("raw_text"),
                json.dumps(source_metadata),
            ),
        )
        row = cur.fetchone()
        candidate_id = row[0]
        is_insert = row[1]
        ingested.append((candidate_id, data))
        if is_insert:
            inserted += 1
        else:
            updated += 1

    conn.commit()
    cur.close()
    conn.close()

    # Index all ingested candidates in Pinecone
    for candidate_id, data in ingested:
        index_candidate(
            candidate_id=candidate_id,
            raw_text=data.get("raw_text", ""),
            metadata={
                "name":           data.get("name"),
                "location":       data.get("location"),
                "candidate_role": data.get("current_role"),
                "skills":         data.get("skills", []),
                "source":         data.get("source"),
            }
        )

    return {
        "status": "success",
        "inserted": inserted,
        "updated": updated,
        "total": len(candidates),
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


@app.get("/candidates/{id}")
def get_candidate(id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT id, name, email, phone, location, "current_role",
               experience_years, skills, stage, source, source_metadata
        FROM candidates WHERE id = %s
    ''',
        (id,),
    )
    r = cur.fetchone()
    cur.close()
    conn.close()
    if not r:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {
        "id": r[0],
        "name": r[1],
        "email": r[2],
        "phone": r[3],
        "location": r[4],
        "role": r[5],
        "exp": r[6],
        "skills": r[7],
        "stage": r[8],
        "source": r[9],
        "source_metadata": r[10],
    }

@app.patch("/candidates/{id}/stage")
async def update_stage(id: int, stage: str):
    candidate = _get_candidate_by_id(id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    normalized_stage = (stage or "").strip().lower()
    previous_stage = (candidate.get("stage") or "").strip().lower()
    should_sync_hire = (
        normalized_stage == "hired"
        and previous_stage != "hired"
        and candidate.get("source") != "bamboohr"
    )

    if should_sync_hire:
        await _push_candidate_to_hrms(candidate)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE candidates SET stage=%s WHERE id=%s", (stage, id))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "updated"}


@app.post("/integrations/bamboohr/push/{id}")
async def push_candidate_to_bamboohr(id: int):
    candidate = _get_candidate_by_id(id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    result = await _push_candidate_to_hrms(candidate)
    return {"status": "synced", "candidate_id": id, "bamboohr": result}

@app.post("/integrations/bamboohr/sync")
async def bamboo_sync():
    await sync_bamboo_candidates(_upsert_candidate)
    return {"status": "synced"}


@app.post("/search/index-all")
def index_all():
    """Index all existing PostgreSQL candidates into Pinecone."""
    conn = get_connection()
    updated = _fill_missing_candidate_values(conn)
    index_all_existing_candidates(conn)
    conn.close()
    return {
        "status": "success",
        "message": "All candidates indexed in Pinecone",
        "filled_missing_rows": updated,
    }


@app.post("/candidates/fill-missing")
def fill_missing_candidates():
    """One-time helper to fill null/blank candidate fields with safe defaults."""
    conn = get_connection()
    updated = _fill_missing_candidate_values(conn)
    conn.close()
    return {"status": "success", "updated_rows": updated}


@app.get("/search")
def semantic_search(q: str, limit: int = 10):
    """Natural language search using Pinecone + sentence-transformers."""
    if not q:
        return []

    # Get ranked candidate IDs from Pinecone
    pinecone_results = search_candidates(q, top_k=limit)
    if not pinecone_results:
        return []

    candidate_ids = [int(r["id"]) for r in pinecone_results]
    scores        = {int(r["id"]): r["score"] for r in pinecone_results}

    # Fetch full profiles from PostgreSQL
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT id, name, email, location, "current_role",
               experience_years, skills, stage, source
        FROM candidates
        WHERE id = ANY(%s)
    """, (candidate_ids,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Return results sorted by Pinecone similarity score
    candidates = [{
        "id":       r[0],
        "name":     r[1],
        "email":    r[2],
        "location": r[3],
        "role":     r[4],
        "exp":      r[5],
        "skills":   r[6],
        "stage":    r[7],
        "source":   r[8],
        "score":    scores.get(r[0], 0)
    } for r in rows]

    return sorted(candidates, key=lambda x: x["score"], reverse=True)


