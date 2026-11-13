"""Persistent pgvector storage and parameterized metadata filtering."""
from typing import Any
import psycopg
from psycopg import sql
from .models import Chunk


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        if dimensions <= 0:
            raise ValueError("Invalid embedding dimensions")
        self.database_url = database_url
        self.dimensions = dimensions

    @staticmethod
    def _vector(values: list[float]) -> str:
        return "[" + ",".join(str(float(value)) for value in values) + "]"

    def create_schema(self) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
            connection.execute(sql.SQL("""CREATE TABLE IF NOT EXISTS chunks (
                strategy TEXT NOT NULL, chunk_id TEXT NOT NULL,
                document_id TEXT NOT NULL, source TEXT NOT NULL, page INTEGER NOT NULL,
                text TEXT NOT NULL, metadata JSONB NOT NULL,
                embedding vector({}) NOT NULL,
                PRIMARY KEY (strategy, chunk_id))""").format(sql.SQL(str(self.dimensions))))
            row = connection.execute("SELECT atttypmod FROM pg_attribute WHERE attrelid='chunks'::regclass AND attname='embedding'").fetchone()
            if row and row[0] != self.dimensions:
                raise ValueError(f"Existing vector dimension {row[0]} differs from {self.dimensions}")

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("Chunk/vector count mismatch")
        if any(len(vector) != self.dimensions for vector in vectors):
            raise ValueError("Embedding dimension mismatch")
        from psycopg.types.json import Jsonb
        with psycopg.connect(self.database_url) as connection:
            # Replace the entire strategy atomically, removing stale chunks on rerun.
            connection.execute("DELETE FROM chunks WHERE strategy=%s", (strategy,))
            with connection.cursor() as cursor:
                cursor.executemany("""INSERT INTO chunks
                    (strategy,chunk_id,document_id,source,page,text,metadata,embedding)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector)""",
                    [(strategy, chunk.chunk_id, chunk.document_id, chunk.source,
                      chunk.page, chunk.text, Jsonb(chunk.metadata), self._vector(vector))
                     for chunk, vector in zip(chunks, vectors)])

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if len(query_vector) != self.dimensions or top_k < 1:
            raise ValueError("Invalid query vector or top_k")
        filters = filters or {}
        if set(filters) - {"chapter"}:
            raise ValueError("Unsupported metadata filter")
        query = """SELECT chunk_id,document_id,source,page,text,metadata,
            1-(embedding <=> %s::vector) AS score FROM chunks WHERE strategy=%s"""
        params: list[Any] = [self._vector(query_vector), strategy]
        if "chapter" in filters:
            query += " AND metadata->>'chapter'=%s"
            params.append(filters["chapter"])
        query += " ORDER BY embedding <=> %s::vector, chunk_id LIMIT %s"
        params.extend([self._vector(query_vector), top_k])
        with psycopg.connect(self.database_url) as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(zip(("chunk_id", "document_id", "source", "page", "text", "metadata", "score"), row))
                for row in rows]
