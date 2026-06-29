#!/usr/bin/env python3
"""
CLI tool to ingest documents into the LMS knowledge base.

Usage:
  python ingest_data.py --file path/to/doc.pdf --title "My Document"
  python ingest_data.py --url https://example.com/article --type url
  python ingest_data.py --url "Machine learning" --type wiki --title "ML Wiki"
"""
import argparse
import asyncio
import sys
import os

# Ensure backend package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from core.database import AsyncSessionLocal
from services.ingestion_service import ingest_file, ingest_url


async def main():
    parser = argparse.ArgumentParser(description="Ingest documents into the LMS knowledge base.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to a PDF or image file")
    group.add_argument("--url", help="URL or Wikipedia page title to ingest")

    parser.add_argument("--title", help="Title for the knowledge asset", default="")
    parser.add_argument("--type", choices=["pdf", "image", "url", "wiki", "youtube"], default="pdf",
                        help="Source type (default: pdf)")
    args = parser.parse_args()

    async with AsyncSessionLocal() as db:
        if args.file:
            file_path = args.file
            if not os.path.exists(file_path):
                print(f"❌  File not found: {file_path}")
                sys.exit(1)
            with open(file_path, "rb") as f:
                content = f.read()
            title = args.title or os.path.basename(file_path)
            print(f"📄  Ingesting file: {file_path} ({len(content):,} bytes) …")
            result = await ingest_file(
                title=title,
                source_type=args.type,
                file_bytes=content,
                filename=os.path.basename(file_path),
                uploaded_by=None,
                db=db,
            )
        else:
            title = args.title or args.url
            print(f"🌐  Ingesting {args.type}: {args.url} …")
            result = await ingest_url(
                url=args.url,
                source_type=args.type,
                uploaded_by=None,
                db=db,
            )

    print(f"✅  Done! Asset ID: {result['asset_id']}")
    print(f"    Chunks stored: {result['chunks_stored']}")
    print(f"    {result['message']}")


if __name__ == "__main__":
    asyncio.run(main())
