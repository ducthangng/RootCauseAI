import psycopg2
from pgvector.psycopg2 import register_vector
from contextlib import contextmanager

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "rootcauseai",
    "user": "rootcauseai",
    "password": "changeme",
}

@contextmanager
def get_conn():
    conn = psycopg2.connect(**DB_CONFIG)
    register_vector(conn)  # lets psycopg2 accept python list -> pgvector type
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()