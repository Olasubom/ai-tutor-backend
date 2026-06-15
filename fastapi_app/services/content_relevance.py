"""Filter catalog content to a learner's enrolled courses."""

from __future__ import annotations

import re
from typing import Any, Dict, List

_STOPWORDS = frozenset({"of", "and", "the", "in", "to", "for", "a", "an", "i", "ii", "iii", "iv"})


def _course_keywords(enrolled_courses: List[Dict[str, Any]]) -> set[str]:
    keywords: set[str] = set()
    for course in enrolled_courses:
        title = str(course.get("title") or course.get("course_title") or "")
        code = str(course.get("code") or course.get("course_code") or "")
        if code:
            keywords.add(code.lower())
        for word in re.findall(r"\w+", title.lower()):
            if word not in _STOPWORDS and len(word) > 2:
                keywords.add(word)
    return keywords


def filter_content_by_enrolled_courses(
    content_items: List[Dict[str, Any]],
    enrolled_courses: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Filter content items to those relevant to enrolled course titles.
    Uses keyword overlap between course titles and item title/description.
    """
    if not enrolled_courses:
        return content_items

    course_keywords = _course_keywords(enrolled_courses)
    if not course_keywords:
        return []

    relevant: List[Dict[str, Any]] = []
    for item in content_items:
        item_text = f"{item.get('title', '')} {item.get('description', '')} {item.get('topic', '')}".lower()
        item_words = set(re.findall(r"\w+", item_text))
        overlap = course_keywords & item_words
        if overlap:
            scored = dict(item)
            scored["_relevance_score"] = len(overlap)
            relevant.append(scored)

    relevant.sort(key=lambda x: x.get("_relevance_score", 0), reverse=True)
    return relevant


def _title_keywords(title: str) -> set[str]:
    return {
        word
        for word in re.findall(r"\w+", title.lower())
        if word not in _STOPWORDS and len(word) > 2
    }


def filter_content_for_course(
    content_items: List[Dict[str, Any]],
    course: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Match content items to a single course using its title/code only.

    Stricter than filter_content_by_enrolled_courses: requires ~50% of the
    course title's significant words to overlap item text, or an exact topic match.
    """
    title = str(course.get("title") or course.get("course_title") or "").strip()
    code = str(course.get("code") or course.get("course_code") or "").strip()
    if not title and not code:
        return []

    course_words = _title_keywords(title)
    title_lower = title.lower()
    matched: List[Dict[str, Any]] = []

    for item in content_items:
        item_topic = str(item.get("topic", "")).lower().strip()
        if title_lower and item_topic == title_lower:
            scored = dict(item)
            scored["_match_score"] = 100
            matched.append(scored)
            continue

        if code and code.lower() in (
            str(item.get("title", "")).lower(),
            str(item.get("description", "")).lower(),
            item_topic,
        ):
            scored = dict(item)
            scored["_match_score"] = 50
            matched.append(scored)
            continue

        if not course_words:
            continue

        item_text = f"{item.get('title', '')} {item.get('description', '')}".lower()
        item_words = set(re.findall(r"\w+", item_text))
        overlap = course_words & item_words
        if len(overlap) / len(course_words) >= 0.5:
            scored = dict(item)
            scored["_match_score"] = len(overlap)
            matched.append(scored)

    matched.sort(key=lambda x: x.get("_match_score", 0), reverse=True)
    return matched


_GENERIC_WORDS = frozenset(
    {
        "law",
        "laws",
        "legal",
        "studies",
        "introduction",
        "intro",
        "principles",
        "systems",
        "system",
        "and",
        "of",
        "the",
        "i",
        "ii",
        "iii",
        "iv",
        "fundamentals",
        "general",
        "basic",
        "advanced",
    }
)


def filter_content_for_course_strict(
    content_items: List[Any],
    course: Dict[str, Any],
) -> List[Any]:
    """
    Strict external-content matching: requires ALL distinctive course-title
    words to appear in item title/description.
    """
    title = str(course.get("title") or course.get("course_title") or "").strip()
    if not title:
        return []

    title_words = {
        word
        for word in re.findall(r"\w+", title.lower())
        if word not in _STOPWORDS and len(word) > 2
    }
    distinctive_words = title_words - _GENERIC_WORDS

    if not distinctive_words:
        course_lower = title.lower()
        matched: List[Any] = []
        for item in content_items:
            item_title = _item_text_field(item, "title").lower()
            if course_lower in item_title or item_title in course_lower:
                matched.append(item)
        return matched

    matched = []
    for item in content_items:
        item_text = (
            f"{_item_text_field(item, 'title')} {_item_text_field(item, 'description')}"
        ).lower()
        item_words = set(re.findall(r"\w+", item_text))
        if distinctive_words.issubset(item_words):
            matched.append(item)
    return matched


def _item_text_field(item: Any, field: str) -> str:
    if isinstance(item, dict):
        return str(item.get(field) or "")
    return str(getattr(item, field, "") or "")
