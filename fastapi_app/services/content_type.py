"""Normalize content source types for API responses and catalog loading."""

from __future__ import annotations

from typing import Any, Dict, Optional


_TYPE_MAP: Dict[str, str] = {
    "ebook": "ebook",
    "book": "ebook",
    "pdf": "ebook",
    "youtube": "video",
    "video": "video",
    "interactive": "interactive",
    "quiz": "quiz",
    "article": "article",
    "text": "article",
    "audio": "audio",
    "simulation": "simulation",
    "practice": "practice",
    "game": "practice",
    "read_aloud": "audio",
    "internal": "interactive",
    "EBOOK": "ebook",
    "VIDEO": "video",
    "ARTICLE": "article",
    "INTERACTIVE": "interactive",
    "QUIZ": "quiz",
    "AUDIO": "audio",
    "PRACTICE": "practice",
    "GAME": "practice",
    "READ_ALOUD": "audio",
    "PDF": "ebook",
    "BOOK": "ebook",
    "YOUTUBE": "video",
    "TEXT": "article",
}


def infer_source_type_from_title(title: str, source_type: Optional[str]) -> str:
    lowered = (title or "").lower()
    if "ebook" in lowered or "e-book" in lowered:
        return "ebook"
    if source_type:
        return source_type
    return "article"


def normalize_source_type(source_type: Optional[str], title: Optional[str] = None) -> str:
    inferred = infer_source_type_from_title(title or "", source_type)
    key = inferred.strip()
    if not key:
        return "article"
    mapped = _TYPE_MAP.get(key) or _TYPE_MAP.get(key.lower())
    if mapped:
        return mapped
    return key.lower().replace(" ", "_")


def normalize_content_item(item: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(item)
    title = str(item.get("title") or "")
    raw_type = item.get("source_type") or item.get("modality")
    canonical = normalize_source_type(str(raw_type or ""), title)
    normalized["source_type"] = canonical
    modality = str(item.get("modality") or "").lower()
    if canonical == "video" and modality != "video":
        normalized["modality"] = "video"
    elif canonical == "ebook" and modality not in {"text", "read_aloud"}:
        normalized["modality"] = "text"
    elif canonical == "interactive" and modality != "interactive":
        normalized["modality"] = "interactive"
    return normalized
