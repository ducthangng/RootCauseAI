import os
import psycopg2
from typing import List
from .node_types import AgentState, RetrievedDoc, log
from .clients import embed_model

def get_db_connection():
    return psycopg2.connect(
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
    )


def retrieve_node(state: AgentState) -> dict:
    log("retrieve", state)

    # nomic yêu cầu prefix "search_query: " cho query, "search_document: " cho doc lúc ingest
    # đây KHÔNG phải tùy chọn — bỏ prefix này thì recall giảm rõ rệt theo docs của nomic
    query_text = f"search_query: {state['incident_text']}"
    query_vector = embed_model.encode(query_text, normalize_embeddings=True).tolist()

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, cmplid, odino, mfr_name, modeltxt, compdesc, cdescr, 1 - (embedding <=> %s::vector) AS score
                    FROM complaints
                ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """,
                (query_vector, query_vector, 20),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    docs: List[RetrievedDoc] = [
        {
            "id": r[0],
            "cmplid": r[1],
            "odino": r[2],
            "mfr_name": r[3],
            "modeltxt": r[4],
            "compdesc": r[5],
            "cdescr": r[6],
            "score": float(r[7]),
        }
        for r in rows
    ]

    print(f"    -> tìm thấy {len(docs)} vụ tương tự (top score={docs[0]['score']:.3f})" if docs else "    -> không tìm thấy vụ nào")
    return {"retrieved_docs": docs}