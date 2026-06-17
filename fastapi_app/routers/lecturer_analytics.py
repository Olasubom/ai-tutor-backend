"""Lecturer analytics read-only endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fastapi_app.admin.models import Course
from fastapi_app.auth.models import User
from fastapi_app.auth.utils import require_role
from fastapi_app.database import get_db
from fastapi_app.services import lecturer_analytics_service as svc
from fastapi_app.services import lecturer_course_service as course_svc

router = APIRouter(prefix="/lecturer/courses", tags=["Lecturer Analytics"])


def _user(db: Session, current: dict) -> User:
    user = db.get(User, current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _assert_access(db: Session, user: User, course_id: str) -> Course:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    try:
        course_svc.assert_lecturer_owns_course(db, user, course)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return course


@router.get("/{course_id}/analytics/overview")
def analytics_overview(
    course_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    _assert_access(db, _user(db, current), course_id)
    try:
        return svc.get_course_overview(db, course_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{course_id}/analytics/students")
def analytics_students(
    course_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    _assert_access(db, _user(db, current), course_id)
    return svc.get_course_students_analytics(db, course_id)


@router.get("/{course_id}/analytics/modules/{module_id}")
def analytics_module(
    course_id: str,
    module_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    _assert_access(db, _user(db, current), course_id)
    try:
        return svc.get_module_analytics(db, course_id, module_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
