"""Hybrid semantic + full-text search endpoint."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from models.db_models import User
from schemas.pydantic_schemas import SearchIn, SearchOut, SearchResultItem
from services.search_service import hybrid_search

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", response_model=SearchOut)
async def search(
    body: SearchIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    """Hybrid semantic + keyword search over the knowledge base."""
    results = await hybrid_search(query=body.query, db=db, top_k=body.top_k)
    return SearchOut(
        results=[
            SearchResultItem(
                chunk_id=r["id"],
                text=r["text"],
                score=r["score"],
                metadata=r.get("metadata"),
            )
            for r in results
        ]
    )
