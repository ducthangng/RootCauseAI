import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
from contextlib import contextmanager
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from server.domain.entity import ProcessJobMessage
from .conn import get_conn

EMBED_MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"
EMBED_DIM = 768  # must match `vector(768)` in schema.sql
BATCH_SIZE_EMBED = 64

# nomic-embed-text requires trust_remote_code=True (custom rotary-embedding arch)
# and device='mps' to actually use the M3 Pro GPU instead of falling back to CPU.
_model = SentenceTransformer(EMBED_MODEL_NAME, trust_remote_code=True, device="mps")

def insert_job_queue(job: ProcessJobMessage):
    return

def embed_batch(texts: list[str]) -> list[list[float]]:
    # Nomic REQUIRES this task prefix on anything you store/search as a document —
    # skip it and retrieval quality silently degrades, no error thrown.
    prefixed = [f"search_document: {t if isinstance(t, str) else ''}" for t in texts]
    embeddings = _model.encode(
        prefixed,
        batch_size=BATCH_SIZE_EMBED,
        show_progress_bar=True,
        normalize_embeddings=True,  # required: we index with vector_cosine_ops
    )
    return embeddings.tolist()


def insert_dataframe(df, table="complaints", batch_size=500):
    # 1. lowercase all column names to match schema.sql
    df = df.rename(columns=str.lower)

    # 2. embed the summary column into a new 'embedding' column — one batched
    #    GPU call instead of N separate requests. Nomic's context window is
    #    8192 tokens, so unlike bge-large, no truncation dance is needed here
    #    for realistic complaint-summary lengths.
    if "embedding" not in df.columns:
        df["embedding"] = embed_batch(df["summary"].tolist())

    cols = list(df.columns)
    col_str = ", ".join(cols)
    query = f"INSERT INTO {table} ({col_str}) VALUES %s"

    records = [tuple(row) for row in df[cols].itertuples(index=False, name=None)]

    with get_conn() as conn:
        with conn.cursor() as cur:
            n_batches = (len(records) + batch_size - 1) // batch_size
            for i in tqdm(range(0, len(records), batch_size), total=n_batches, desc="Inserting batches"):
                execute_values(cur, query, records[i:i + batch_size])

