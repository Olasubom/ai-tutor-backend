"""One-time / admin utilities for lecturer_id on catalog courses."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.admin.models import Course, Department
from fastapi_app.auth.models import User


def backfill_lecturer_ids_by_department(db: Session) -> dict:
    """
    For each course with lecturer_id NULL, assign the first active lecturer
    in that course's department (by department name match).
    """
    courses = db.scalars(select(Course).where(Course.lecturer_id.is_(None))).all()
    assigned = 0
    skipped = 0
    details: List[dict] = []

    dept_lecturers: dict[str, str] = {}
    lecturers = db.scalars(
        select(User).where(User.role == "lecturer", User.lecturer_status == "active")
    ).all()
    for lec in lecturers:
        if lec.department and lec.department not in dept_lecturers:
            dept_lecturers[lec.department] = lec.id

    dept_by_id = {d.id: d for d in db.scalars(select(Department)).all()}

    for course in courses:
        dept = dept_by_id.get(course.department_id)
        if not dept:
            skipped += 1
            continue
        lecturer_id = dept_lecturers.get(dept.name)
        if not lecturer_id:
            skipped += 1
            details.append({"course_id": course.id, "code": course.course_code, "status": "no_lecturer"})
            continue
        course.lecturer_id = lecturer_id
        assigned += 1
        details.append(
            {"course_id": course.id, "code": course.course_code, "lecturer_id": lecturer_id, "status": "assigned"}
        )

    if assigned:
        db.commit()
    return {"assigned": assigned, "skipped": skipped, "details": details}


def assign_lecturer_to_course(
    db: Session,
    course_id: str,
    lecturer_id: Optional[str] = None,
) -> Course:
    course = db.get(Course, course_id)
    if not course:
        raise ValueError("Course not found")

    if lecturer_id:
        lecturer = db.get(User, lecturer_id)
        if not lecturer or lecturer.role != "lecturer":
            raise ValueError("Lecturer not found")
        course.lecturer_id = lecturer_id
    else:
        dept = db.get(Department, course.department_id)
        if not dept:
            raise ValueError("Department not found")
        lecturer = db.scalars(
            select(User).where(
                User.role == "lecturer",
                User.department == dept.name,
                User.lecturer_status == "active",
            )
        ).first()
        if not lecturer:
            raise ValueError("No active lecturer found for this department")
        course.lecturer_id = lecturer.id

    db.commit()
    db.refresh(course)
    return course
