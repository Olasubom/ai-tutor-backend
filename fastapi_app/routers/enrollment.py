"""Student and lecturer enrollment routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fastapi_app.auth.models import User
from fastapi_app.auth.utils import get_current_user, require_role
from fastapi_app.database import get_db
from fastapi_app.services import enrollment_service as svc
from fastapi_app.services import lecturer_course_service as course_svc

router = APIRouter(tags=["Enrollment"])


@router.post("/student/courses/{course_id}/enroll")
def student_enroll(
    course_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("student"))] = None,
):
    try:
        row = svc.enroll_student(db, current["user_id"], course_id)
        return {"id": row.id, "course_id": row.course_id, "status": row.status}
    except ValueError as exc:
        msg = str(exc)
        if "Already enrolled" in msg:
            raise HTTPException(status_code=409, detail=msg) from exc
        raise HTTPException(status_code=400, detail=msg) from exc


@router.delete("/student/courses/{course_id}/enroll")
def student_drop(
    course_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("student"))] = None,
):
    try:
        svc.drop_enrollment(db, current["user_id"], course_id)
        return {"message": "Dropped course"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/student/courses")
def student_courses(
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("student"))] = None,
):
    return svc.list_student_enrollments(db, current["user_id"])


@router.get("/lecturer/courses/{course_id}/students")
def lecturer_course_students(
    course_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    user = db.get(User, current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    from fastapi_app.admin.models import Course

    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    try:
        course_svc.assert_lecturer_owns_course(db, user, course)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return svc.list_course_students(db, course_id)


@router.delete("/lecturer/courses/{course_id}/students/{student_id}")
def remove_student(
    course_id: str,
    student_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    user = db.get(User, current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    from fastapi_app.admin.models import Course

    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    try:
        course_svc.assert_lecturer_owns_course(db, user, course)
        svc.remove_student_from_course(db, course_id, student_id)
        return {"message": "Student removed"}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
