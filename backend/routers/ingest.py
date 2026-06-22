"""Document ingestion router — PDF, URL, Wiki → chunks → pgvector."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import require_admin
from models.db_models import User
from schemas.pydantic_schemas import IngestOut, IngestURLIn
from services.ingestion_service import ingest_file, ingest_url

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post("/file", response_model=IngestOut)
async def ingest_document_file(
    title: Annotated[str, Form()],
    source_type: Annotated[str, Form()] = "pdf",
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Upload a PDF or image file for ingestion into the vector store."""
    if file.content_type not in ("application/pdf", "image/png", "image/jpeg", "image/jpg"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Supported types: PDF, PNG, JPEG",
        )
    contents = await file.read()
    result = await ingest_file(
        title=title,
        source_type=source_type,
        file_bytes=contents,
        filename=file.filename or "upload",
        uploaded_by=admin.id,
        db=db,
    )
    return result


@router.post("/url", response_model=IngestOut)
async def ingest_url_or_wiki(
    body: IngestURLIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    """Ingest content from a URL or Wikipedia page."""
    result = await ingest_url(
        url=body.url,
        source_type=body.source_type,
        uploaded_by=admin.id,
        db=db,
    )
    return result
