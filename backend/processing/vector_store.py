import os
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

PINECONE_API_KEY  = os.getenv("PINECONE_API_KEY")
INDEX_NAME        = os.getenv("PINECONE_INDEX_NAME", "recruitment-index")

# Load embedding model once at startup (runs locally, no API cost)
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
print("Embedding model ready.")
EMBEDDING_DIM = model.get_sentence_embedding_dimension()

pc = Pinecone(api_key=PINECONE_API_KEY)


def _sanitize_metadata(metadata: dict | None) -> dict:
    metadata = metadata or {}

    def _clean_scalar(value) -> str:
        if value is None:
            return ""
        return str(value).strip()

    raw_skills = metadata.get("skills")
    if isinstance(raw_skills, (list, tuple, set)):
        skills = ", ".join(
            [str(skill).strip() for skill in raw_skills if skill is not None and str(skill).strip()]
        )
    else:
        skills = _clean_scalar(raw_skills)

    return {
        "name": _clean_scalar(metadata.get("name")),
        "location": _clean_scalar(metadata.get("location")),
        "candidate_role": _clean_scalar(metadata.get("candidate_role")),
        "source": _clean_scalar(metadata.get("source")),
        "skills": skills,
    }


def get_or_create_index():
    """Get existing Pinecone index or create it."""
    existing = [i.name for i in pc.list_indexes()]
    target_index = INDEX_NAME

    if INDEX_NAME in existing:
        # If an index already exists with a different dimension, switch to a compatible one.
        index_info = pc.describe_index(INDEX_NAME)
        existing_dim = getattr(index_info, "dimension", None)
        if existing_dim is None and isinstance(index_info, dict):
            existing_dim = index_info.get("dimension")

        if existing_dim and existing_dim != EMBEDDING_DIM:
            target_index = f"{INDEX_NAME}-{EMBEDDING_DIM}"
            if target_index not in existing:
                print(
                    f"Index '{INDEX_NAME}' has dimension {existing_dim}; "
                    f"creating '{target_index}' with dimension {EMBEDDING_DIM}."
                )
                pc.create_index(
                    name=target_index,
                    dimension=EMBEDDING_DIM,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )
                print("Compatible index created.")
    else:
        print(f"Creating Pinecone index '{INDEX_NAME}'...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=EMBEDDING_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        print("Index created.")

    return pc.Index(target_index)


def index_candidate(candidate_id: int, raw_text: str, metadata: dict):
    """Embed candidate text and store in Pinecone."""
    if not raw_text:
        print(f"Skipping candidate {candidate_id} — no raw_text")
        return

    index     = get_or_create_index()
    embedding = model.encode(raw_text).tolist()
    clean_metadata = _sanitize_metadata(metadata)

    index.upsert(vectors=[{
        "id":       str(candidate_id),
        "values":   embedding,
        "metadata": clean_metadata,
    }])
    print(f"Indexed candidate {candidate_id} in Pinecone")


def search_candidates(query: str, top_k: int = 10) -> list[dict]:
    """Embed query and find similar candidates in Pinecone."""
    index           = get_or_create_index()
    query_embedding = model.encode(query).tolist()

    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True
    )
    return [
        {
            "id":       match["id"],
            "score":    round(match["score"], 3),
            "metadata": match.get("metadata", {}),
        }
        for match in results["matches"]
    ]


def index_all_existing_candidates(conn):
    """Index all candidates already in PostgreSQL — run once."""
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, location, "current_role",
               skills, source, raw_text
        FROM candidates
        WHERE raw_text IS NOT NULL
    """)
    rows = cur.fetchall()
    cur.close()

    print(f"Indexing {len(rows)} existing candidates in Pinecone...")
    for r in rows:
        index_candidate(
            candidate_id=r[0],
            raw_text=r[6],
            metadata={
                "name":           r[1],
                "location":       r[2],
                "candidate_role": r[3],
                "skills":         r[4] or [],
                "source":         r[5],
            }
        )
    print("All existing candidates indexed.")

