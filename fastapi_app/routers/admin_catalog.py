from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from fastapi_app.security import require_api_key
from fastapi_app.services.memory_files import read_json, write_json

router = APIRouter(prefix="/admin/catalog", tags=["Admin Catalog"])


def _normalize_level(level: Optional[str]) -> Optional[str]:
    if level is None or str(level).strip() == "":
        return None
    level_clean = str(level).replace(" Level", "").replace("level", "").strip()
    try:
        return str(int(level_clean))
    except (ValueError, TypeError):
        return str(level).strip()


def _catalog_course_dict(course: dict) -> dict:
    return {
        **course,
        "semester": course.get("semester") or "Both",
    }


@router.get("/courses")
def list_courses(
    department_id: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
    _: None = Depends(require_api_key),
) -> List[dict]:
    courses = read_json("courses/catalog.json", [])
    if department_id:
        courses = [c for c in courses if c.get("department_id") == department_id]
    normalized = _normalize_level(level)
    if normalized is not None:
        courses = [c for c in courses if _normalize_level(str(c.get("level", ""))) == normalized]
    return [_catalog_course_dict(c) for c in courses]


@router.post("/courses/sync")
def sync_course(course: dict, _: None = Depends(require_api_key)) -> dict:
    courses = read_json("courses/catalog.json", [])
    cid = course.get("id")
    if cid:
        courses = [c for c in courses if c.get("id") != cid]
    if not course.get("semester"):
        course = {**course, "semester": "Both"}
    courses.append(course)
    write_json("courses/catalog.json", courses)
    return {"ok": True, "count": len(courses)}


@router.delete("/courses/{course_id}")
def delete_course(course_id: str, _: None = Depends(require_api_key)) -> dict:
    courses = read_json("courses/catalog.json", [])
    filtered = [c for c in courses if c.get("id") != course_id]
    write_json("courses/catalog.json", filtered)
    return {"ok": True}
