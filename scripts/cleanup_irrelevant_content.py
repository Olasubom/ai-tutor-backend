"""
Re-validates ingested ebook content_items and removes irrelevant entries.

Run with: python scripts/cleanup_irrelevant_content.py
Add --dry-run to preview without deleting.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / "agency" / ".env", override=True)

from sqlalchemy import delete, select  # noqa: E402

from agency.core.tools.database import Database  # noqa: E402
from agency.core.tools.models import ContentItem  # noqa: E402
from scripts.ingest_ebooks import (  # noqa: E402
    is_likely_relevant_ebook,
    validate_relevance_with_llm,
)

_EBOOK_SOURCE_TYPES = {"ebook", "book", "pdf", "text"}


def _is_ingested_ebook(row: ContentItem) -> bool:
    payload = dict(row.payload_json or {})
    source_origin = str(payload.get("source_origin", "")).strip().lower()
    if source_origin and source_origin != "ingested":
        return False

    item_id = str(row.item_id or "")
    source_type = str(row.source_type or payload.get("source_type", "")).lower()
    if item_id.startswith("book_"):
        return True
    return source_type in _EBOOK_SOURCE_TYPES


def _topic_for_item(row: ContentItem) -> str:
    payload = dict(row.payload_json or {})
    return str(row.topic or payload.get("topic") or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove irrelevant ingested ebook items")
    parser.add_argument("--dry-run", action="store_true", help="Preview removals without deleting")
    parser.add_argument("--skip-llm", action="store_true", help="Use heuristic filter only")
    args = parser.parse_args()

    db = Database()
    removed = 0
    checked = 0

    with db._SessionLocal() as session:  # noqa: SLF001
        rows = list(session.scalars(select(ContentItem)).all())
        ebook_rows = [row for row in rows if _is_ingested_ebook(row)]
        print(f"Checking {len(ebook_rows)} ingested ebook items...")

        to_delete: list[str] = []
        for item in ebook_rows:
            checked += 1
            topic = _topic_for_item(item)
            if not topic:
                print(f"[SKIP] No topic for item: {item.title}")
                continue

            payload = dict(item.payload_json or {})
            book_data = {
                "title": item.title,
                "description": str(payload.get("description") or ""),
            }

            relevant = is_likely_relevant_ebook(book_data, topic)
            if relevant and not args.skip_llm:
                relevant = validate_relevance_with_llm(
                    item.title,
                    str(payload.get("description") or ""),
                    topic,
                )

            if relevant:
                continue

            action = "WOULD REMOVE" if args.dry_run else "REMOVING"
            print(f"[{action}] ({topic}) {item.title}")
            to_delete.append(item.item_id)
            removed += 1

        if not args.dry_run and to_delete:
            session.execute(delete(ContentItem).where(ContentItem.item_id.in_(to_delete)))
            session.commit()

    label = "Would remove" if args.dry_run else "Removed"
    print(f"\n{label} {removed} of {checked} checked items.")


if __name__ == "__main__":
    main()
