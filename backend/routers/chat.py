"""RAG chatbot router — streaming responses with conversation history."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from models.db_models import User
from schemas.pydantic_schemas import ChatMessageIn
from services.rag_service import stream_rag_response

router = APIRouter(prefix="/chat", tags=["RAG Chatbot"])


@router.post("/")
async def chat(
    body: ChatMessageIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Stream a RAG-augmented response to the user's message."""
    return StreamingResponse(
        stream_rag_response(
            session_id=body.session_id,
            user_id=str(current_user.id),
            user_message=body.message,
            db=db,
        ),
        media_type="text/event-stream",
    )


@router.get("/sessions/{session_id}/history")
async def get_chat_history(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Return past messages for a given session."""
    from sqlalchemy import select
    from models.db_models import ChatMessage

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id, ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]
