import json

from processing.normaliser import normalise_skills


def parse_linkedin_profile(payload: dict) -> dict:
    """Normalize a LinkedIn profile payload into candidate DB shape."""
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    if not email:
        raise ValueError("email is required for LinkedIn ingestion")

    skills = normalise_skills(payload.get("skills", []))
    current_role = str(payload.get("current_role", "")).strip() or str(payload.get("headline", "")).strip()

    work_history = payload.get("work_history", [])
    education = payload.get("education", [])
    source_metadata = {
        "profile_url": payload.get("profile_url", ""),
        "about": payload.get("about", ""),
        "work_history": work_history,
        "education": education,
    }

    normalized = {
        "name": name,
        "email": email,
        "phone": str(payload.get("phone", "")).strip(),
        "country": str(payload.get("country", "")).strip(),
        "location": str(payload.get("location", "")).strip(),
        "current_role": current_role,
        "experience_years": int(payload.get("experience_years", 0) or 0),
        "skills": skills,
        "source": "linkedin",
        "raw_text": json.dumps(payload, ensure_ascii=True),
        "source_metadata": source_metadata,
        "work_history": work_history,
        "education": education,
    }
    return normalized

