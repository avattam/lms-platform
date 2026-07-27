"""RAG service — hybrid search (pgvector + FTS) + streaming response via AI Service (OpenAI / Ollama)."""
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import ChatMessage
from services.ai_service import get_embedding, stream_chat_response


async def _embed(text_input: str) -> list[float]:
    """Generate vector embedding via unified AI service (OpenAI / Ollama)."""
    return await get_embedding(text_input)


async def _hybrid_search(query: str, db: AsyncSession, top_k: int = 5) -> list[dict]:
    """
    Reciprocal Rank Fusion of:
    - Vector similarity search (pgvector cosine)
    - Full-text search (PostgreSQL tsvector)
    """
    embedding = await _embed(query)
    embedding_str = f"[{','.join(str(v) for v in embedding)}]"

    sql = text("""
        WITH semantic AS (
            SELECT id, chunk_text, metadata,
                   1 - (embedding <=> CAST(:embedding AS vector)) AS sem_score,
                   ROW_NUMBER() OVER (ORDER BY embedding <=> CAST(:embedding AS vector)) AS sem_rank
            FROM document_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        ),
        keyword AS (
            SELECT id, chunk_text, metadata,
                   ts_rank(to_tsvector('english', chunk_text), plainto_tsquery('english', :query)) AS kw_score,
                   ROW_NUMBER() OVER (
                       ORDER BY ts_rank(to_tsvector('english', chunk_text), plainto_tsquery('english', :query)) DESC
                   ) AS kw_rank
            FROM document_chunks
            WHERE to_tsvector('english', chunk_text) @@ plainto_tsquery('english', :query)
            LIMIT :top_k
        ),
        fused AS (
            SELECT
                COALESCE(s.id, k.id) AS id,
                COALESCE(s.chunk_text, k.chunk_text) AS chunk_text,
                COALESCE(s.metadata, k.metadata) AS metadata,
                (1.0 / (60 + COALESCE(s.sem_rank, 999))) +
                (1.0 / (60 + COALESCE(k.kw_rank, 999))) AS rrf_score
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
    return [{"id": str(r.id), "text": r.chunk_text, "metadata": r.metadata, "score": r.rrf_score} for r in rows]


async def _get_history(session_id: str, user_id: str, db: AsyncSession, last_n: int = 6) -> str:
    """Load last N chat turns for context."""
    from sqlalchemy import select
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(last_n)
    )
    messages = result.scalars().all()
    messages.reverse()
    history = "\n".join(f"{m.role.upper()}: {m.content}" for m in messages)
    return history


async def _save_messages(session_id: str, user_id: str, user_msg: str, ai_msg: str, db: AsyncSession):
    db.add(ChatMessage(session_id=session_id, user_id=user_id, role="human", content=user_msg))
    db.add(ChatMessage(session_id=session_id, user_id=user_id, role="ai", content=ai_msg))
    await db.commit()


async def stream_rag_response(
    session_id: str,
    user_id: str,
    user_message: str,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Stream SSE-formatted RAG response tokens."""
    # Retrieve context
    chunks = await _hybrid_search(user_message, db)
    context = "\n\n".join(f"[Source {i+1}]\n{c['text']}" for i, c in enumerate(chunks))
    history = await _get_history(session_id, user_id, db)

    prompt = f"""You are a helpful learning assistant for an educational platform.
Use the following retrieved context to answer the student's question accurately and concisely.
If the context does not contain the answer, say so honestly.

=== CONTEXT ===
{context}

=== CONVERSATION HISTORY ===
{history}

=== STUDENT QUESTION ===
{user_message}

=== YOUR ANSWER ==="""

    full_response = ""
    async for sse_chunk in stream_chat_response(prompt, temperature=0.7):
        yield sse_chunk
        if sse_chunk.startswith("data: ") and not sse_chunk.startswith("data: [DONE]"):
            try:
                import json as _json
                payload_data = _json.loads(sse_chunk[6:].strip())
                full_response += payload_data.get("token", "")
            except Exception:
                pass

    # Persist conversation
    await _save_messages(session_id, user_id, user_message, full_response, db)
