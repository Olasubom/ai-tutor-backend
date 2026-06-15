"""Per-course curriculum generation from content catalog."""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.core.context import get_runtime
from agency.core.tools.models import ContentItem
from agency.tutor_service import _normalize_catalog_item_types
from fastapi_app.admin.models import Course
from fastapi_app.services.content_relevance import filter_content_for_course_strict
from fastapi_app.services.course_service import get_course_ids_for_learner
from fastapi_app.services.module_progress_service import build_modules_from_items


def _course_dict(course: Course) -> Dict[str, Any]:
    return {
        "id": course.id,
        "code": course.course_code,
        "title": course.course_title,
        "course_code": course.course_code,
        "course_title": course.course_title,
    }


def _external_ingested_items(db: Session) -> List[ContentItem]:
    rows = db.scalars(
        select(ContentItem).where(ContentItem.course_id.is_(None))
    ).all()
    ingested: List[ContentItem] = []
    for row in rows:
        payload = dict(row.payload_json or {})
        origin = str(payload.get("source_origin") or "").strip().lower()
        if origin == "ingested" or str(row.item_id or "").startswith(("yt_", "book_")):
            ingested.append(row)
    return ingested


def get_curriculum_for_course(learner_id: str, course_id: str, db: Session) -> Dict[str, Any]:
    """Build curriculum modules for one enrolled course."""
    enrolled_ids = get_course_ids_for_learner(learner_id)
    if course_id not in enrolled_ids:
        return {
            "learner_id": learner_id,
            "course_id": course_id,
            "course_code": "",
            "course_title": "",
            "modules": [],
            "source": None,
            "status": "not_enrolled",
            "message": "You are not enrolled in this course.",
        }

    course = db.get(Course, course_id)
    if not course:
        return {
            "learner_id": learner_id,
            "course_id": course_id,
            "course_code": "",
            "course_title": "",
            "modules": [],
            "source": None,
            "status": "not_found",
            "message": "Course not found.",
        }

    uploaded_items = list(
        db.scalars(
            select(ContentItem)
            .where(
                ContentItem.course_id == course_id,
                ContentItem.status == "approved",
            )
            .order_by(ContentItem.module_order.asc().nullslast(), ContentItem.created_at.asc())
        ).all()
    )

    if uploaded_items:
        modules = build_modules_from_items(uploaded_items, learner_id, db)
        return {
            "learner_id": learner_id,
            "course_id": course.id,
            "course_code": course.course_code,
            "course_title": course.course_title,
            "modules": modules,
            "source": "lecturer_materials",
            "status": "generated",
        }

    external_rows = _external_ingested_items(db)
    course_payload = _course_dict(course)
    external_dicts = [_normalize_catalog_item_types(_row_to_dict(row)) for row in external_rows]
    relevant_dicts = filter_content_for_course_strict(external_dicts, course_payload)

    if relevant_dicts:
        by_id = {row.item_id: row for row in external_rows}
        relevant_rows = [by_id[d["id"]] for d in relevant_dicts if d.get("id") in by_id]
        modules = build_modules_from_items(relevant_rows, learner_id, db)
        return {
            "learner_id": learner_id,
            "course_id": course.id,
            "course_code": course.course_code,
            "course_title": course.course_title,
            "modules": modules,
            "source": "external_supplemental",
            "status": "generated",
        }

    return {
        "learner_id": learner_id,
        "course_id": course.id,
        "course_code": course.course_code,
        "course_title": course.course_title,
        "modules": [],
        "source": None,
        "status": "not_generated",
        "message": (
            f"No content is available yet for {course.course_code}. "
            "Request an AI update or ask your lecturer to upload materials."
        ),
    }


def _row_to_dict(row: ContentItem) -> Dict[str, Any]:
    payload = dict(row.payload_json or {})
    payload.setdefault("id", row.item_id)
    payload.setdefault("title", row.title)
    payload.setdefault("topic", row.topic)
    payload.setdefault("description", payload.get("description") or "")
    payload.setdefault("modality", row.modality)
    payload.setdefault("source_type", row.source_type)
    payload.setdefault("source_url", row.source_url)
    payload.setdefault("course_id", row.course_id)
    payload.setdefault("module_order", row.module_order)
    payload.setdefault("status", row.status)
    return payload
