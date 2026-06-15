from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / "agency" / ".env", override=True)

from agency.core.context import get_runtime  # noqa: E402
from agency.core.tools.source_ingestion import fetch_ebook_learning_items  # noqa: E402

_BLOCKLIST_PATTERNS = [
    r"\bcalendar\b",
    r"\balmanac\b",
    r"\badres[- ]?kalendar\b",
    r"\bpurim\b",
    r"\bhanukkah\b",
    r"\bdirectory\b",
    r"\byearbook\b",
    r"\bgazetteer\b",
    r"\bregister\b",
]

_STOPWORDS = frozenset(
    {"of", "and", "the", "in", "to", "for", "a", "an", "i", "ii", "iii", "iv", "introduction"}
)


def is_likely_relevant_ebook(book_data: dict, topic: str) -> bool:
    """
    Heuristic filter to reject obviously irrelevant OpenLibrary results
    before they reach content_items.
    """
    title = (book_data.get("title") or "").lower()

    for pattern in _BLOCKLIST_PATTERNS:
        if re.search(pattern, title):
            return False

    ascii_letters = sum(1 for c in title if c.isascii() and c.isalpha())
    total_letters = sum(1 for c in title if c.isalpha())
    if total_letters > 0 and (ascii_letters / total_letters) < 0.8:
        return False

    topic_words = {
        word
        for word in re.findall(r"\w+", topic.lower())
        if word not in _STOPWORDS and len(word) > 3
    }
    title_words = set(re.findall(r"\w+", title))
    description = (book_data.get("description") or "").lower()
    desc_words = set(re.findall(r"\w+", description))

    if topic_words and not (topic_words & title_words or topic_words & desc_words):
        return False

    return True


def validate_relevance_with_llm(title: str, description: str, topic: str) -> bool:
    """
    Uses GPT-4o-mini to confirm a book is a legitimate study resource for the topic.
    On API failure, defaults to True (fail open).
    """
    import os

    if not os.getenv("OPENAI_API_KEY", "").strip():
        return True

    try:
        from openai import OpenAI

        client = OpenAI()
        prompt = (
            f"A university student is studying the topic: '{topic}'.\n\n"
            f"Is this book a relevant academic study resource for that topic?\n"
            f"Title: {title}\n"
            f"Description: {description[:300]}\n\n"
            f"Answer with only YES or NO."
        )
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_VALIDATION_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
            temperature=0,
        )
        answer = (response.choices[0].message.content or "").strip().upper()
        return answer.startswith("YES")
    except Exception as exc:
        print(f"[VALIDATION] LLM check failed: {exc}")
        return True


def _filter_ebook_candidates(
    candidates: List[Dict[str, Any]],
    *,
    max_per_topic: int,
    use_llm: bool = True,
) -> List[Dict[str, Any]]:
    accepted: List[Dict[str, Any]] = []
    per_topic: Dict[str, int] = {}

    for book in candidates:
        topic = str(book.get("topic") or "").strip()
        if not topic:
            continue
        if per_topic.get(topic, 0) >= max_per_topic:
            continue

        book_data = {
            "title": book.get("title", ""),
            "description": book.get("description", ""),
        }
        if not is_likely_relevant_ebook(book_data, topic):
            print(f"[SKIP] Irrelevant result for '{topic}': {book.get('title')}")
            continue

        if use_llm and not validate_relevance_with_llm(
            str(book.get("title", "")),
            str(book.get("description", "")),
            topic,
        ):
            print(f"[SKIP-LLM] Rejected for '{topic}': {book.get('title')}")
            continue

        accepted.append(book)
        per_topic[topic] = per_topic.get(topic, 0) + 1

    return accepted


def ingest_ebooks_for_topics(
    topics: List[str],
    max_per_topic: int = 3,
    *,
    use_llm_validation: bool = True,
) -> Dict[str, Any]:
    runtime = get_runtime()
    if runtime.repository is None:
        raise RuntimeError("Repository unavailable. Configure DATABASE_URL first.")

    clean_topics = [str(t).strip() for t in topics if str(t).strip()]
    if not clean_topics:
        return {"source": "ebooks", "topics": [], "fetched": 0, "written": 0, "filtered": 0}

    candidates = fetch_ebook_learning_items(
        topics=clean_topics,
        max_per_topic=max_per_topic,
        candidates_per_topic=max(max_per_topic * 8, 15),
    )
    items = _filter_ebook_candidates(
        candidates,
        max_per_topic=max_per_topic,
        use_llm=use_llm_validation,
    )
    written = runtime.repository.upsert_content_items(items)
    runtime.catalog = runtime.repository.list_content_items(limit=5000) or runtime.catalog
    return {
        "source": "ebooks",
        "topics": clean_topics,
        "fetched": len(candidates),
        "filtered": len(items),
        "written": written,
    }


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

    result = ingest_ebooks_for_topics(topics, max_per_topic=3)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
