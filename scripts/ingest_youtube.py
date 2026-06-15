from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / "agency" / ".env", override=True)

from agency.core.context import get_runtime  # noqa: E402
from agency.core.tools.source_ingestion import fetch_youtube_learning_items  # noqa: E402


def ingest_youtube_for_topics(topics: List[str], max_per_topic: int = 3) -> Dict[str, Any]:
    runtime = get_runtime()
    if runtime.repository is None:
        raise RuntimeError("Repository unavailable. Configure DATABASE_URL first.")

    clean_topics = [str(t).strip() for t in topics if str(t).strip()]
    if not clean_topics:
        return {"source": "youtube", "topics": [], "fetched": 0, "written": 0}

    items = fetch_youtube_learning_items(topics=clean_topics, max_per_topic=max_per_topic)
    written = runtime.repository.upsert_content_items(items)
    runtime.catalog = runtime.repository.list_content_items(limit=5000) or runtime.catalog
    return {"source": "youtube", "topics": clean_topics, "fetched": len(items), "written": written}


def main() -> None:
    runtime = get_runtime()
    if runtime.repository is None:
        print("Repository unavailable. Configure DATABASE_URL first.")
        return

    topics = sorted(
        {
            str(item.get("topic"))
            for item in runtime.catalog
            if isinstance(item, dict) and item.get("topic")
        }
    )
    if not topics:
        topics = ["Algebra", "Geometry", "Algorithms", "Python"]

    result = ingest_youtube_for_topics(topics, max_per_topic=3)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
