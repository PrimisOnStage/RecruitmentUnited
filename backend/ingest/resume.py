"""Resume parsing helpers backed by LlamaCloud extraction agents."""

import os
from llama_cloud import LlamaCloud
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from backend.models import CandidateSchema
    from backend.processing.normaliser import normalise_skills
except ImportError:
    from models import CandidateSchema
    from processing.normaliser import normalise_skills

load_dotenv()
client = LlamaCloud()

def get_or_create_agent():
    """Reuse a named extraction agent so all resume parsing shares one schema.

    Creating the agent dynamically keeps local setup simple: the first run creates
    it, and later runs reuse the existing remote configuration.
    """
    agents = client.extraction.extraction_agents.list()
    for agent in agents:
        if agent.name == "resume-parser-v2":
            return agent
    return client.extraction.extraction_agents.create(
        name="resume-parser-v2",
        data_schema=CandidateSchema.model_json_schema(),
        config={}
    )

def parse_resume(file_path: str) -> dict:
    """Upload a PDF resume to LlamaCloud and map the result into our candidate shape."""
    print(f"Uploading {file_path} to LlamaCloud...")
    file = client.files.create(file=file_path, purpose="extract")

    print("Extracting structured data...")
    agent = get_or_create_agent()
    result = client.extraction.jobs.extract(
        extraction_agent_id=agent.id,
        file_id=file.id,
    )

    data = dict(result.data)
    # Skills are normalized here so all downstream filters/search use one vocabulary.
    data["skills"] = normalise_skills(data.get("skills", []))
    data["source"] = "resume"
    # The raw text field is what gets embedded for semantic search later on.
    data["raw_text"] = str(data)
    print(f"Parsed: {data.get('name')} — {len(data.get('skills', []))} skills found")
    return data