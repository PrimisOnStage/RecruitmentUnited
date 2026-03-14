from backend.ingest.linkedin import parse_linkedin_profile
from backend.main import _normalize_candidate_payload


def test_parse_linkedin_profile_uses_headline_when_role_missing():
    payload = {
        "name": "Ada Lovelace",
        "email": "ADA@EXAMPLE.COM",
        "headline": "Principal Engineer",
        "skills": ["ReactJS", "Python", "reactjs"],
        "work_history": [{"company": "Analytical Engines Ltd.", "role": "Engineer", "duration": "3y"}],
        "education": [{"degree": "Math", "institution": "London", "year": "1835"}],
    }

    result = parse_linkedin_profile(payload)

    assert result["email"] == "ada@example.com"
    assert result["current_role"] == "Principal Engineer"
    assert result["skills"] == ["react", "python"]
    assert result["source"] == "linkedin"
    assert result["source_metadata"]["work_history"] == payload["work_history"]


def test_normalize_candidate_payload_lowercases_email_and_builds_fallback_text():
    normalized = _normalize_candidate_payload(
        {
            "name": " Grace Hopper ",
            "email": "GRACE@Example.COM ",
            "skills": "Python, ReactJS, python",
            "experience_years": -4,
            "source": "resume",
        }
    )

    assert normalized["email"] == "grace@example.com"
    assert normalized["skills"] == ["python", "react"]
    assert normalized["experience_years"] == 0
    assert "Grace Hopper" in normalized["raw_text"]
    assert "python, react" in normalized["raw_text"].lower()

