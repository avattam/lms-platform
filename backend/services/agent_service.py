"""Agent Service — Orchestrates LangChain Tutor Agent & persists chat messages."""
import json
import logging
from collections.abc import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.tutor_agent import stream_tutor_agent
from models.db_models import ChatMessage

logger = logging.getLogger(__name__)


async def _get_history(session_id: str, user_id: str, db: AsyncSession, last_n: int = 6) -> list[dict]:
    """Load last N chat turns for context."""
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(last_n)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()
    messages.reverse()
    return [{"role": m.role, "content": m.content} for m in messages]


async def _save_messages(session_id: str, user_id: str, user_msg: str, ai_msg: str, db: AsyncSession):
    """Persist student and AI assistant messages."""
    db.add(ChatMessage(session_id=session_id, user_id=user_id, role="human", content=user_msg))
    db.add(ChatMessage(session_id=session_id, user_id=user_id, role="ai", content=ai_msg))
    await db.commit()


async def stream_agentic_rag_response(
    session_id: str,
    user_id: str,
    user_message: str,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """
    Stream structured SSE agent events while tracking complete text for persistence.
    """
    history = await _get_history(session_id, user_id, db)
    full_text = ""

    async for sse_line in stream_tutor_agent(
        session_id=session_id,
        user_id=user_id,
        user_message=user_message,
        history_messages=history,
        db=db,
    ):
        yield sse_line

        # Accumulate response tokens for storage
        if sse_line.startswith("data: "):
            raw_payload = sse_line[6:].strip()
            try:
                data = json.loads(raw_payload)
                if data.get("type") == "token":
                    full_text += data.get("token", "")
            except Exception:
                pass

    if full_text.strip():
        await _save_messages(session_id, user_id, user_message, full_text, db)
