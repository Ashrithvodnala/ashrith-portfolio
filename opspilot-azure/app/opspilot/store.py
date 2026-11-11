"""pgvector-backed store for runbook chunks."""

from __future__ import annotations

import psycopg


def _vec(embedding: list[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in embedding) + "]"


class VectorStore:
    def __init__(self, dsn: str, dim: int):
        self.dsn = dsn
        self.dim = dim

    def _conn(self):
        return psycopg.connect(self.dsn, autocommit=True)

    def init_schema(self) -> None:
        with self._conn() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(
                f"""CREATE TABLE IF NOT EXISTS chunks (
                    id BIGSERIAL PRIMARY KEY,
                    source TEXT NOT NULL,
                    chunk_index INT NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector({self.dim}) NOT NULL,
                    UNIQUE (source, chunk_index))"""
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)"
            )

    def replace_source(self, source: str, contents: list[str], embeddings: list[list[float]]) -> None:
        with self._conn() as conn, conn.transaction():
            conn.execute("DELETE FROM chunks WHERE source = %s", (source,))
            for i, (content, emb) in enumerate(zip(contents, embeddings)):
                conn.execute(
                    "INSERT INTO chunks (source, chunk_index, content, embedding) VALUES (%s, %s, %s, %s::vector)",
                    (source, i, content, _vec(emb)),
                )

    def search(self, embedding: list[float], k: int) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT source, content, embedding <=> %s::vector AS distance FROM chunks ORDER BY distance LIMIT %s",
                (_vec(embedding), k),
            ).fetchall()
        return [{"source": r[0], "content": r[1], "distance": float(r[2])} for r in rows]

    def ping(self) -> bool:
        with self._conn() as conn:
            conn.execute("SELECT 1")
        return True

    def count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
