"""Shared candidate-normalization helpers used across ingestion and persistence.

These helpers convert source-specific payloads into one canonical candidate shape
so PostgreSQL storage, Pinecone indexing, and the frontend all operate on a
consistent representation.
"""

try:
    from backend.processing.normaliser import normalise_skills
except ImportError:
    import importlib

    normalise_skills = importlib.import_module("processing.normaliser").normalise_skills


def build_filler_raw_text(data: dict) -> str:
    """Create a fallback text blob so every candidate remains searchable/indexable."""
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


def normalize_candidate_payload(data: dict) -> dict:
    """Normalize partial candidate data into the shape expected by storage and search."""
    payload = dict(data or {})

    def _clean_text(value, default=""):
        if value is None:
            return default
        value = str(value).strip()
        return value or default

    raw_skills = payload.get("skills") or []
    if isinstance(raw_skills, str):
        raw_skills = [part.strip() for part in raw_skills.split(",") if part.strip()]
    skills = normalise_skills([str(skill) for skill in raw_skills if skill is not None and str(skill).strip()])

    try:
        experience_years = int(payload.get("experience_years") or 0)
    except (TypeError, ValueError):
        experience_years = 0

    normalized = {
        "name": _clean_text(payload.get("name"), "Unknown Candidate"),
        "email": _clean_text(payload.get("email")).lower(),
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
        normalized["raw_text"] = build_filler_raw_text(normalized)

    return normalized


def build_index_metadata(data: dict) -> dict:
    """Return the compact metadata stored alongside candidate embeddings."""
    return {
        "name": data.get("name"),
        "location": data.get("location"),
        "candidate_role": data.get("current_role"),
        "skills": data.get("skills", []),
        "source": data.get("source"),
    }

