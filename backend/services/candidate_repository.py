"""Database-facing helpers for candidate storage and retrieval.

This module owns SQL interactions so route handlers can focus on HTTP concerns
while higher-level services orchestrate normalization and third-party sync.
"""

import json

from psycopg2.extras import RealDictCursor

try:
    from backend.database import get_connection
    from backend.services.candidate_normalization import normalize_candidate_payload
except ImportError:
    from database import get_connection
    from services.candidate_normalization import normalize_candidate_payload


def fill_missing_candidate_values(conn) -> int:
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


def upsert_candidate(data: dict) -> int:
    """Insert or update a candidate row using email as the stable dedupe key."""
    data = normalize_candidate_payload(data)
    conn = get_connection()
    cur = conn.cursor()
    source_metadata = data.get("source_metadata") or {}

    cur.execute(
        """
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
    candidate_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return candidate_id


def upsert_gmail_candidates(candidates: list[dict]) -> tuple[int, int, list[tuple[int, dict]]]:
    """Upsert Gmail-derived candidates in one transaction and track inserts vs updates."""
    inserted = 0
    updated = 0
    ingested: list[tuple[int, dict]] = []

    conn = get_connection()
    cur = conn.cursor()

    for data in candidates:
        data = normalize_candidate_payload(data)
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
    return inserted, updated, ingested


def get_candidate_by_id(candidate_id: int) -> dict | None:
    """Fetch a minimal candidate record used by stage updates and HR sync."""
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


def list_candidates(
    skill: str | None = None,
    location: str | None = None,
    country: str | None = None,
    min_exp: int | None = None,
) -> list[dict]:
    """List candidates with optional exact-skill and partial text filters."""
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
    if min_exp is not None:
        query += " AND experience_years >= %s"
        params.append(min_exp)
    query += " ORDER BY created_at DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "id": r[0],
            "name": r[1],
            "email": r[2],
            "country": r[3],
            "location": r[4],
            "role": r[5],
            "exp": r[6],
            "skills": r[7],
            "stage": r[8],
            "source": r[9],
        }
        for r in rows
    ]


def get_candidate_detail(candidate_id: int) -> dict | None:
    """Return the full profile view for a single candidate."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT id, name, email, phone, location, "current_role",
               experience_years, skills, stage, source, source_metadata
        FROM candidates WHERE id = %s
        ''',
        (candidate_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "phone": row[3],
        "location": row[4],
        "role": row[5],
        "exp": row[6],
        "skills": row[7],
        "stage": row[8],
        "source": row[9],
        "source_metadata": row[10],
    }


def update_candidate_stage(candidate_id: int, stage: str) -> None:
    """Persist a candidate's stage change in PostgreSQL."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE candidates SET stage=%s WHERE id=%s", (stage, candidate_id))
    conn.commit()
    cur.close()
    conn.close()


def fetch_candidates_by_ids(candidate_ids: list[int]) -> list[dict]:
    """Load candidate display records for a known set of candidate IDs."""
    if not candidate_ids:
        return []

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, email, location, "current_role",
               experience_years, skills, stage, source
        FROM candidates
        WHERE id = ANY(%s)
        """,
        (candidate_ids,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "id": r[0],
            "name": r[1],
            "email": r[2],
            "location": r[3],
            "role": r[4],
            "exp": r[5],
            "skills": r[6],
            "stage": r[7],
            "source": r[8],
        }
        for r in rows
    ]

