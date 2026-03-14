from backend.processing.normaliser import normalise_skills


def test_normalise_skills_applies_aliases_deduplicates_and_preserves_order():
    skills = [" Python ", "ReactJS", "python", "ML", "NodeJS", ""]

    assert normalise_skills(skills) == ["python", "react", "machine learning", "node.js"]

