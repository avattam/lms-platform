"""Standalone hybrid search service — used by both search router and RAG chain."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import httpx
from core.config import settings

OLLAMA_EMBED_URL = f"{settings.OLLAMA_BASE_URL}/api/embeddings"


async def _embed(text_input: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            OLLAMA_EMBED_URL,
            json={"model": settings.EMBED_MODEL, "prompt": text_input},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


async def hybrid_search(
    query: str,
    db: AsyncSession,
    top_k: int = 5,
) -> list[dict]:
    """
    Reciprocal Rank Fusion combining:
    - pgvector cosine similarity (semantic)
    - PostgreSQL tsvector full-text search (keyword)
    Returns ranked list of {id, text, metadata, score}.
    """
    embedding = await _embed(query)
    embedding_str = f"[{','.join(str(v) for v in embedding)}]"

    sql = text("""
        WITH semantic AS (
            SELECT id, chunk_text, metadata,
                   ROW_NUMBER() OVER (ORDER BY embedding <=> :embedding::vector) AS sem_rank
            FROM document_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :embedding::vector
            LIMIT :top_k
        ),
        keyword AS (
            SELECT id, chunk_text, metadata,
                   ROW_NUMBER() OVER (
                       ORDER BY ts_rank(to_tsvector('english', chunk_text),
                                        plainto_tsquery('english', :query)) DESC
                   ) AS kw_rank
            FROM document_chunks
            WHERE to_tsvector('english', chunk_text) @@ plainto_tsquery('english', :query)
            LIMIT :top_k
        ),
        fused AS (
            SELECT
                COALESCE(s.id, k.id)               AS id,
                COALESCE(s.chunk_text, k.chunk_text) AS chunk_text,
                COALESCE(s.metadata, k.metadata)   AS metadata,
                (1.0 / (60 + COALESCE(s.sem_rank, 999))) +
                (1.0 / (60 + COALESCE(k.kw_rank,  999))) AS rrf_score
            FROM semantic s
            FULL OUTER JOIN keyword k ON s.id = k.id
        )
        SELECT id, chunk_text, metadata, rrf_score
        FROM fused
        ORDER BY rrf_score DESC
        LIMIT :top_k;
    """)

    result = await db.execute(
        sql,
        {"embedding": embedding_str, "query": query, "top_k": top_k},
    )
    rows = result.fetchall()
    return [
        {
            "id": str(r.id),
            "text": r.chunk_text,
            "metadata": r.metadata,
            "score": float(r.rrf_score),
        }
        for r in rows
    ]
