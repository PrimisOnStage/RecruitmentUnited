"""Utilities for normalizing skill names into a consistent searchable vocabulary."""

ALIASES = {
    "reactjs": "react",
    "nodejs": "node.js",
    "postgres": "postgresql",
    "js": "javascript",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "k8s": "kubernetes",
    "tf": "tensorflow",
}

def normalise_skills(skills: list[str]) -> list[str]:
    """Lowercase, alias-map, and deduplicate skills while preserving input order."""
    seen = set()
    result = []
    for s in skills:
        # Normalize common shorthand so filtering/searching sees one canonical term.
        clean = ALIASES.get(s.lower().strip(), s.lower().strip())
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result