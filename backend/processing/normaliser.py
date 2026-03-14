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
    seen = set()
    result = []
    for s in skills:
        clean = ALIASES.get(s.lower().strip(), s.lower().strip())
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result