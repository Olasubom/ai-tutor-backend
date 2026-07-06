#!/usr/bin/env python3
"""
One-off script: computes and caches topics.json for all approved ContentItems
that have extracted_text but no cached topic segmentation yet.

Run with: python scripts/backfill_module_topics.py
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
from fastapi_app.services.module_embedding_service import (
    load_topics,
    save_topics,
    segment_module_topics,
)
from fastapi_app.services.module_session_service import _get_subject_context


def main() -> None:
    init_database()
    db = Database()
    backfilled = 0
    skipped = 0

    with db._SessionLocal() as session:  # noqa: SLF001
        items = session.scalars(
            select(ContentItem).where(
                ContentItem.status == "approved",
                ContentItem.extracted_text.isnot(None),
            )
        ).all()

        for item in items:
            text = item.extracted_text or ""
            if not text.strip():
                skipped += 1
                continue

            existing = load_topics(item.item_id, extracted_text=text, db=session)
            if existing:
                skipped += 1
                continue

            subject_ctx = _get_subject_context(item, session)
            payload = segment_module_topics(
                content_item_id=item.item_id,
                extracted_text=text,
                module_title=item.title,
                course_title=subject_ctx.get("course_title", ""),
            )
            save_topics(item.item_id, payload, db=session)
            print(
                f"[BACKFILL] {item.item_id} ({item.title}): "
                f"{len(payload['topics'])} topics via {payload['method']}"
            )
            backfilled += 1

    print(f"\nDone. Backfilled: {backfilled}, Skipped (already cached or empty): {skipped}")


if __name__ == "__main__":
    main()
