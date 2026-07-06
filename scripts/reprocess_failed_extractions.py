#!/usr/bin/env python3
"""Re-run extraction for content items where it previously failed
(extracted_text is None) — e.g. docx uploads processed before docx support existed.
Run with: python scripts/reprocess_failed_extractions.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / "agency" / ".env", override=False)

from sqlalchemy import select

from agency.core.tools.database import Database
from agency.core.tools.models import ContentItem
from fastapi_app.bootstrap import init_database
from fastapi_app.services.module_embedding_service import process_content_item_embeddings


def main() -> None:
    init_database()
    db = Database()
    with db._SessionLocal() as session:  # noqa: SLF001
        items = session.scalars(
            select(ContentItem).where(
                ContentItem.extracted_text.is_(None),
                ContentItem.source_type.in_(["document", "pdf"]),
            )
        ).all()
        ids = [i.item_id for i in items]

    print(f"Found {len(ids)} content item(s) with missing extracted_text.")
    for cid in ids:
        print(f"Reprocessing {cid}...")
        process_content_item_embeddings(cid)
    print("Done. Restart the backend, then start a NEW session for each affected module.")


if __name__ == "__main__":
    main()
