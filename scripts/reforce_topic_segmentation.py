#!/usr/bin/env python3
"""Force re-segmentation for specific content items, ignoring any existing
cache (disk or DB). Use after fixing the segmentation prompt/ordering logic.
Run with: python scripts/reforce_topic_segmentation.py
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
    _topics_json_path,
    save_topics,
    segment_module_topics,
)
from fastapi_app.services.module_session_service import _get_subject_context

TARGET_TITLE_PREFIX = "CIL201 Module"


def main() -> None:
    init_database()
    db = Database()
    with db._SessionLocal() as session:  # noqa: SLF001
        items = session.scalars(
            select(ContentItem).where(ContentItem.title.ilike(f"{TARGET_TITLE_PREFIX}%"))
        ).all()

        for item in items:
            if not item.extracted_text:
                print(f"SKIP {item.item_id} ({item.title}) — no extracted_text")
                continue

            disk_path = _topics_json_path(item.item_id)
            if disk_path.exists():
                disk_path.unlink()

            item.topics_json = None
            session.commit()

            subject_ctx = _get_subject_context(item, session)
            payload = segment_module_topics(
                content_item_id=item.item_id,
                extracted_text=item.extracted_text,
                module_title=item.title,
                course_title=subject_ctx.get("course_title", ""),
            )
            save_topics(item.item_id, payload, db=session)

            titles = [t["title"] for t in payload["topics"]]
            print(f"{item.item_id} | {item.title} | method={payload['method']} | {len(titles)} topics:")
            for t in titles:
                print(f"  - {t}")
            print()


if __name__ == "__main__":
    main()
