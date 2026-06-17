"""Course lookup helpers for enrolled learners."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.admin.models import Course
from fastapi_app.auth.memory import get_structured_memory
from fastapi_app.services.memory_files import read_json


def _course_payload(c: Course) -> Dict[str, Any]:
    return {
        "id": c.id,
        "course_code": c.course_code,
        "course_title": c.course_title,
        "level": c.level,
        "department_id": c.department_id,
        "semester": c.semester or "Both",
        "credit_units": c.credit_units,
        "course_type": c.course_type,
    }


def get_course_ids_for_learner(learner_id: str, db: Session | None = None) -> List[str]:
    """Resolve enrolled course IDs from memory, onboarding, and CourseEnrollment rows."""
    mem = get_structured_memory(learner_id)
    ids: set[str] = {str(i) for i in (mem.get("courses") or []) if i}

    onboarding = read_json(f"onboarding/{learner_id}.json", {}).get("data", {})
    step2 = onboarding.get("step2") or {}
    for i in step2.get("selected_course_ids") or []:
        if i:
            ids.add(str(i))

    try:
        from agency.core.tools.database import Database
        from fastapi_app.models.lecturer_dashboard import CourseEnrollment

        session = db
        own_session = False
        if session is None:
            session = Database()._SessionLocal()  # noqa: SLF001
            own_session = True
        rows = session.scalars(
            select(CourseEnrollment.course_id).where(
                CourseEnrollment.student_id == learner_id,
                CourseEnrollment.status == "active",
            )
        ).all()
        ids.update(str(r) for r in rows)
        if own_session:
            session.close()
    except Exception:
        pass

    return list(ids)


def get_courses_by_ids(db: Session, course_ids: List[str]) -> List[Dict[str, Any]]:
    if not course_ids:
        return []
    rows = db.scalars(select(Course).where(Course.id.in_(course_ids))).all()
    by_id = {c.id: _course_payload(c) for c in rows}
    return [by_id[i] for i in course_ids if i in by_id]


def get_learner_enrolled_courses(learner_id: str, db: Session) -> List[Dict[str, Any]]:
    """Course metadata for a learner's enrolled course IDs."""
    course_ids = get_course_ids_for_learner(learner_id)
    if not course_ids:
        return []
    courses = get_courses_by_ids(db, course_ids)
    return [
        {
            "id": c["id"],
            "code": c["course_code"],
            "title": c["course_title"],
            "level": c["level"],
            "semester": c.get("semester") or "Both",
            "credit_units": c["credit_units"],
            "course_type": c["course_type"],
        }
        for c in courses
    ]


def build_enrolled_course_context(enrolled: List[Dict[str, Any]]) -> str:
    if not enrolled:
        return ""
    lines = [
        f"- {c['code']}: {c['title']} (Level {c['level']}, Semester {c.get('semester') or 'Both'})"
        for c in enrolled
    ]
    course_context = "\n".join(lines)
    return (
        f"This student is enrolled in these university courses:\n{course_context}\n"
        "Generate curriculum and recommend resources relevant to these specific courses. "
        "Do not recommend unrelated subjects like algebra unless the student is enrolled in math courses."
    )
