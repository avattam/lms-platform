"""Ingestion service — parse documents and store chunks + embeddings."""
import io
import uuid
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.db_models import DocumentChunk, KnowledgeAsset

from langchain_text_splitters import RecursiveCharacterTextSplitter
# pyrefly: ignore [missing-import]
from langchain_ollama import OllamaEmbeddings

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

def _split_text(text: str) -> list[str]:
    """LangChain RecursiveCharacterTextSplitter."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    docs = splitter.create_documents([text])
    return [doc.page_content for doc in docs]

async def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch embed texts via LangChain OllamaEmbeddings."""
    embeddings_model = OllamaEmbeddings(
        model=settings.EMBED_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )
    return await embeddings_model.aembed_documents(texts)


async def _store_chunks(
    asset: KnowledgeAsset,
    chunks: list[str],
    embeddings: list[list[float]],
    db: AsyncSession,
    extra_metadata: dict | None = None,
) -> int:
    for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        chunk = DocumentChunk(
            asset_id=asset.id,
            chunk_text=chunk_text,
            chunk_index=i,
            embedding=embedding,
            metadata_={**(extra_metadata or {}), "chunk_index": i},
        )
        db.add(chunk)
    await db.commit()
    return len(chunks)


async def ingest_file(
    title: str,
    source_type: str,
    file_bytes: bytes,
    filename: str,
    uploaded_by: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """Parse a PDF or image file and store chunks in pgvector."""
    try:
        from unstructured.partition.auto import partition

        elements = partition(file=io.BytesIO(file_bytes), metadata_filename=filename)
        raw_text = "\n".join(str(e) for e in elements if str(e).strip())
    except ImportError:
        # Fallback: treat as plain text (for testing without unstructured)
        raw_text = file_bytes.decode("utf-8", errors="ignore")

    asset = KnowledgeAsset(
        title=title,
        source_type=source_type,
        source_uri=filename,
        uploaded_by=uploaded_by,
    )
    db.add(asset)
    await db.flush()

    chunks = _split_text(raw_text)
    embeddings = await _embed_texts(chunks)
    count = await _store_chunks(asset, chunks, embeddings, db, {"filename": filename})

    return {"asset_id": asset.id, "chunks_stored": count, "message": f"Ingested {count} chunks from {filename}."}


async def ingest_url(
    url: str,
    source_type: str,
    uploaded_by: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """Fetch and ingest content from a URL or Wikipedia page."""
    if source_type == "wiki":
        try:
            # pyrefly: ignore [missing-import]
            import wikipedia
            # Extract page title from URL or use URL as search term
            page_title = url.split("/wiki/")[-1].replace("_", " ") if "/wiki/" in url else url
            page = wikipedia.page(page_title)
            raw_text = page.content
            title = page.title
        except Exception as e:
            raise ValueError(f"Could not fetch Wikipedia page: {e}")
    else:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            raw_text = soup.get_text(separator="\n", strip=True)
            title = soup.title.string if soup.title else url
        except ImportError:
            raw_text = resp.text
            title = url

    asset = KnowledgeAsset(
        title=title or url,
        source_type=source_type,
        source_uri=url,
        uploaded_by=uploaded_by,
    )
    db.add(asset)
    await db.flush()

    chunks = _split_text(raw_text)
    embeddings = await _embed_texts(chunks)
    count = await _store_chunks(asset, chunks, embeddings, db, {"source_url": url})

    return {"asset_id": asset.id, "chunks_stored": count, "message": f"Ingested {count} chunks from {url}."}
