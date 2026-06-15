"""Admin-triggered content ingestion from course catalog topics."""

from __future__ import annotations

import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.admin.models import Course, Department
from fastapi_app.services.memory_files import read_json, write_json

logger = logging.getLogger(__name__)

INGESTION_LOG_PATH = "ingestion_log.json"
NO_CONTENT_MESSAGE = (
    "No personalized resources are available yet for your enrolled courses. "
    "Your administrator can generate content for your department from the admin panel."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_ingestion_status() -> Dict[str, Any]:
    return read_json(INGESTION_LOG_PATH, {})


def write_ingestion_status(payload: Dict[str, Any]) -> None:
    write_json(INGESTION_LOG_PATH, payload)


def topics_from_courses(
    db: Session,
    *,
    college_id: Optional[str] = None,
    department_id: Optional[str] = None,
) -> List[str]:
    q = select(Course)
    if department_id:
        q = q.where(Course.department_id == department_id)
    elif college_id:
        q = q.join(Department, Course.department_id == Department.id).where(Department.college_id == college_id)

    courses = db.scalars(q).all()
    topics = sorted({c.course_title.strip() for c in courses if c.course_title and c.course_title.strip()})
    return topics


def run_ingestion_for_topics(topics: List[str], max_per_topic: int = 3) -> Dict[str, Any]:
    """Run YouTube + ebook ingestion for the given topics and log status."""
    from scripts.ingest_ebooks import ingest_ebooks_for_topics
    from scripts.ingest_youtube import ingest_youtube_for_topics

    started = _now_iso()
    log: Dict[str, Any] = {
        "last_run": started,
        "started_at": started,
        "status": "running",
        "topics": topics,
        "items_added": 0,
        "errors": [],
    }
    write_ingestion_status(log)

    total_added = 0

    if not os.getenv("YOUTUBE_API_KEY", "").strip():
        log["errors"].append(
            {
                "source": "youtube",
                "error": "YOUTUBE_API_KEY not set. YouTube ingestion will be skipped.",
                "traceback": "",
            }
        )

    try:
        yt_result = ingest_youtube_for_topics(topics, max_per_topic=max_per_topic)
        total_added += int(yt_result.get("written", 0) or 0)
    except Exception as exc:
        logger.exception("ingest_youtube_failed")
        log["errors"].append(
            {
                "source": "youtube",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        )

    try:
        book_result = ingest_ebooks_for_topics(topics, max_per_topic=max_per_topic)
        total_added += int(book_result.get("written", 0) or 0)
    except Exception as exc:
        logger.exception("ingest_ebooks_failed")
        log["errors"].append(
            {
                "source": "ebooks",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        )

    if total_added > 0:
        status = "completed" if not log["errors"] else "partial"
    elif log["errors"]:
        status = "failed"
    else:
        status = "completed_no_results"

    log["status"] = status
    log["items_added"] = total_added
    log["last_run"] = _now_iso()
    write_ingestion_status(log)
    return log
