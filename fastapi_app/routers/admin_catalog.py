from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from fastapi_app.security import require_api_key
from fastapi_app.services.memory_files import read_json, write_json

router = APIRouter(prefix="/admin", tags=["Admin Catalog"])


@router.get("/courses")
def list_courses(
    department_id: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
    _: None = Depends(require_api_key),
) -> List[dict]:
    courses = read_json("courses/catalog.json", [])
    if department_id:
        courses = [c for c in courses if c.get("department_id") == department_id]
    if level:
        courses = [c for c in courses if str(c.get("level")) == str(level)]
    return courses


@router.post("/courses/sync")
def sync_course(course: dict, _: None = Depends(require_api_key)) -> dict:
    courses = read_json("courses/catalog.json", [])
    cid = course.get("id")
    if cid:
        courses = [c for c in courses if c.get("id") != cid]
    courses.append(course)
    write_json("courses/catalog.json", courses)
    return {"ok": True, "count": len(courses)}


@router.delete("/courses/{course_id}")
def delete_course(course_id: str, _: None = Depends(require_api_key)) -> dict:
    courses = read_json("courses/catalog.json", [])
    filtered = [c for c in courses if c.get("id") != course_id]
    write_json("courses/catalog.json", filtered)
    return {"ok": True}
