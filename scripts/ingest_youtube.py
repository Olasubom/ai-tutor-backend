from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / "agency" / ".env", override=True)

from agency.core.context import get_runtime  # noqa: E402
from agency.core.tools.source_ingestion import fetch_youtube_learning_items  # noqa: E402


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

    items = fetch_youtube_learning_items(topics=topics, max_per_topic=3)
    written = runtime.repository.upsert_content_items(items)
    print(json.dumps({"source": "youtube", "topics": topics, "fetched": len(items), "written": written}, indent=2))


if __name__ == "__main__":
    main()

