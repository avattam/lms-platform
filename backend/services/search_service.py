"""Standalone hybrid search service — used by both search router and RAG chain."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.ai_service import get_embedding


async def _embed(text_input: str) -> list[float]:
    """Generate vector embedding via unified AI service (OpenAI / Ollama)."""
    return await get_embedding(text_input)


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
                   ROW_NUMBER() OVER (ORDER BY embedding <=> CAST(:embedding AS vector)) AS sem_rank
            FROM document_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:embedding AS vector)
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
