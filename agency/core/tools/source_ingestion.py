from __future__ import annotations

import os
from typing import Any, Dict, List

import httpx


def _normalize_topic(topic: str) -> str:
    return " ".join(topic.strip().split())


def _clean_text(value: Any) -> str:
    """Best-effort sanitization for API text fields."""
    text = str(value or "").strip()
    return text.encode("utf-8", "ignore").decode("utf-8", "ignore")


def fetch_youtube_learning_items(topics: List[str], max_per_topic: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch YouTube educational videos and normalize them to content item schema.

    Requires `YOUTUBE_API_KEY` in environment.
    """
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        print("[WARNING] YOUTUBE_API_KEY not set. YouTube ingestion will be skipped.")
        return []

    out: List[Dict[str, Any]] = []
    with httpx.Client(timeout=20.0) as client:
        for topic in topics:
            query = f"{_normalize_topic(topic)} tutorial"
            resp = client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "maxResults": max_per_topic,
                    "key": api_key,
                    "safeSearch": "strict",
                    "videoEmbeddable": "true",
                },
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            for item in data.get("items", []):
                vid = item.get("id", {}).get("videoId")
                sn = item.get("snippet", {})
                if not vid:
                    continue
                out.append(
                    {
                        "id": f"yt_{vid}",
                        "topic": _clean_text(topic),
                        "title": _clean_text(sn.get("title", f"{topic} video")),
                        "description": _clean_text(sn.get("description", "")),
                        "modality": "video",
                        "bloom_level": "understand",
                        "difficulty": "medium",
                        "duration_minutes": 12,
                        "tags": [topic.lower(), "youtube", "video"],
                        "prerequisites": [],
                        "source_type": "youtube",
                        "provider": "YouTube",
                        "source_url": f"https://www.youtube.com/watch?v={vid}",
                        "quality_score": 0.75,
                        "source_origin": "ingested",
                    }
                )
    return out


def fetch_ebook_learning_items(
    topics: List[str],
    max_per_topic: int = 5,
    *,
    candidates_per_topic: int | None = None,
) -> List[Dict[str, Any]]:
    """
    Fetch ebook-like resources from OpenLibrary search API.

    No API key required. Use candidates_per_topic to over-fetch before relevance filtering.
    """
    api_limit = max(candidates_per_topic or max_per_topic, max_per_topic)
    out: List[Dict[str, Any]] = []
    with httpx.Client(timeout=20.0) as client:
        for topic in topics:
            resp = client.get(
                "https://openlibrary.org/search.json",
                params={"q": topic, "limit": api_limit},
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            for doc in data.get("docs", []):
                key = doc.get("key")
                title = doc.get("title")
                if not key or not title:
                    continue
                work_id = str(key).strip("/").replace("/", "_")
                subject_names = doc.get("subject", []) or []
                description = _clean_text(
                    f"Reading resource for {topic}. "
                    f"Subjects: {', '.join(str(s) for s in subject_names[:5])}"
                    if subject_names
                    else f"Reading resource for {topic}"
                )
                out.append(
                    {
                        "id": f"book_{work_id}",
                        "topic": _clean_text(topic),
                        "title": _clean_text(title),
                        "description": description,
                        "modality": "text",
                        "bloom_level": "understand",
                        "difficulty": "medium",
                        "duration_minutes": 20,
                        "tags": [topic.lower(), "ebook", "reading"],
                        "prerequisites": [],
                        "source_type": "ebook",
                        "provider": "OpenLibrary",
                        "source_url": f"https://openlibrary.org{key}",
                        "quality_score": 0.65,
                        "source_origin": "ingested",
                    }
                )
    return out

