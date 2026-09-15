# clients.py
import os
from .node_types import AgentState, log
from langsmith.wrappers import wrap_openai
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from psycopg2 import pool

os.environ["TOKENIZERS_PARALLELISM"] = "false"

load_dotenv()

openai_client = wrap_openai(OpenAI(api_key=os.environ["OPENAI_API_KEY"]))
embed_model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True, device="mps")

db_pool = pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    dbname=os.environ["DB_NAME"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    host=os.environ.get("DB_HOST", "localhost"),
    port=os.environ.get("DB_PORT", "5432"),
)

def log(node_name: str, state: AgentState) -> None:
    print(f"\n>>> ĐANG CHẠY NODE: {node_name}")
    print(f"    revision_count={state['revision_count']}  status={state['status']}")