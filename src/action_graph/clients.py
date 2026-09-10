# clients.py
import os
from .node_types import AgentState, log
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer

load_dotenv()

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
embed_model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True, device="mps")

def log(node_name: str, state: AgentState) -> None:
    print(f"\n>>> ĐANG CHẠY NODE: {node_name}")
    print(f"    revision_count={state['revision_count']}  status={state['status']}")