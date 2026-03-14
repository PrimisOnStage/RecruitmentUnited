import os
from llama_cloud import LlamaCloud
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import CandidateSchema
from processing.normaliser import normalise_skills

load_dotenv()
client = LlamaCloud()

def get_or_create_agent():
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
    print(f"Uploading {file_path} to LlamaCloud...")
    file = client.files.create(file=file_path, purpose="extract")

    print("Extracting structured data...")
    agent = get_or_create_agent()
    result = client.extraction.jobs.extract(
        extraction_agent_id=agent.id,
        file_id=file.id,
    )

    data = dict(result.data)
    data["skills"] = normalise_skills(data.get("skills", []))
    data["source"] = "resume"
    data["raw_text"] = str(data)
    print(f"Parsed: {data.get('name')} — {len(data.get('skills', []))} skills found")
    return data