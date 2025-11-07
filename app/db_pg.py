import psycopg
from psycopg.rows import dict_row
from typing import List, Dict, Any
from config import EMBED_DIM, PG_IVFFLAT_LISTS, PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD_FILE
from utils import read_secret, vector_literal

def _dsn() -> str:
    pw = read_secret(PG_PASSWORD_FILE)
    return f"host={PG_HOST} port={PG_PORT} dbname={PG_DB} user={PG_USER} password={pw}"

def init_pg_schema():
    with psycopg.connect(_dsn(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS documents (
                    id BIGSERIAL PRIMARY KEY,
                    source TEXT,
                    chunk_id INT,
                    content TEXT,
                    embedding vector({EMBED_DIM})
                );
            """)
            cur.execute(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_documents_embedding_ivfflat_l2'
                    ) THEN
                        CREATE INDEX idx_documents_embedding_ivfflat_l2
                        ON documents
                        USING ivfflat (embedding vector_l2_ops)
                        WITH (lists = {PG_IVFFLAT_LISTS});
                    END IF;
                END$$;
            """)

def replace_source(source: str, chunks: List[str], embeddings: List[List[float]]):
    with psycopg.connect(_dsn(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE source = %s;", (source,))
            for i, (chunk, vec) in enumerate(zip(chunks, embeddings)):
                cur.execute(
                    f"INSERT INTO documents (source, chunk_id, content, embedding) VALUES (%s, %s, %s, %s::vector({EMBED_DIM}));",
                    (source, i, chunk, vector_literal(vec))
                )

def query_topk(qvec: List[float], k: int) -> List[Dict[str, Any]]:
    with psycopg.connect(_dsn()) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT id, source, chunk_id, content,
                       (embedding <-> %s::vector({EMBED_DIM})) AS l2_dist
                FROM documents
                ORDER BY embedding <-> %s::vector({EMBED_DIM})
                LIMIT %s;
                """,
                (vector_literal(qvec), vector_literal(qvec), k)
            )
            rows = cur.fetchall()
    hits = []
    for r in rows:
        d = float(r["l2_dist"])
        sim = 1.0 - (d*d)/2.0  # cosine ~ via normalized L2
        hits.append({
            "id": int(r["id"]),
            "source": r["source"],
            "chunk_id": int(r["chunk_id"]),
            "content": r["content"][:400],
            "score": sim
        })
    return hits
