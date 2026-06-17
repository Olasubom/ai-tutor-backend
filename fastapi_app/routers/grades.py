"""Formal grade assignment routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.admin.models import Course
from fastapi_app.auth.models import User
from fastapi_app.auth.utils import require_role
from fastapi_app.database import get_db
from fastapi_app.models.lecturer_dashboard import Grade
from fastapi_app.schemas.lecturer_dashboard import GradeCreate, GradeUpdate
from fastapi_app.services import grade_service
from fastapi_app.services import lecturer_course_service as course_svc
from fastapi_app.services import notifications_service

router = APIRouter(tags=["Grades"])


def _user(db: Session, current: dict) -> User:
    user = db.get(User, current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/lecturer/courses/{course_id}/grades")
def submit_grade(
    course_id: str,
    payload: GradeCreate,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    user = _user(db, current)
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    try:
        course_svc.assert_lecturer_owns_course(db, user, course)
        row = grade_service.upsert_grade(
            db,
            student_id=payload.student_id,
            course_id=course_id,
            lecturer_id=user.id,
            ca_score=payload.ca_score,
            exam_score=payload.exam_score,
            comment=payload.comment,
        )
        student = db.get(User, payload.student_id)
        notifications_service.create_user_notification(
            db,
            payload.student_id,
            title=f"Grade posted for {course.course_code}",
            message=f"Your grade: {row.grade_letter} ({row.total_score}%)",
            notification_type="grade_posted",
        )
        return grade_service.grade_to_dict(
            row,
            student_name=student.name if student else "",
            student_email=student.email if student else "",
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/lecturer/courses/{course_id}/grades")
def list_course_grades(
    course_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    user = _user(db, current)
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    try:
        course_svc.assert_lecturer_owns_course(db, user, course)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    rows = db.scalars(select(Grade).where(Grade.course_id == course_id)).all()
    out = []
    for g in rows:
        student = db.get(User, g.student_id)
        out.append(
            grade_service.grade_to_dict(
                g,
                student_name=student.name if student else "",
                student_email=student.email if student else "",
            )
        )
    return out


@router.put("/lecturer/grades/{grade_id}")
def update_grade(
    grade_id: str,
    payload: GradeUpdate,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    row = db.get(Grade, grade_id)
    if not row:
        raise HTTPException(status_code=404, detail="Grade not found")
    user = _user(db, current)
    course = db.get(Course, row.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    try:
        course_svc.assert_lecturer_owns_course(db, user, course)
        updated = grade_service.upsert_grade(
            db,
            student_id=row.student_id,
            course_id=row.course_id,
            lecturer_id=user.id,
            ca_score=payload.ca_score if payload.ca_score is not None else row.ca_score,
            exam_score=payload.exam_score if payload.exam_score is not None else row.exam_score,
            comment=payload.comment if payload.comment is not None else row.comment,
        )
        student = db.get(User, row.student_id)
        return grade_service.grade_to_dict(
            updated,
            student_name=student.name if student else "",
            student_email=student.email if student else "",
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/lecturer/courses/{course_id}/grades/export")
def export_grades(
    course_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    user = _user(db, current)
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    try:
        course_svc.assert_lecturer_owns_course(db, user, course)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    csv_content = grade_service.export_grades_csv(db, course_id)
    return Response(content=csv_content, media_type="text/csv")


@router.get("/student/grades")
def student_all_grades(
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("student"))] = None,
):
    rows = db.scalars(select(Grade).where(Grade.student_id == current["user_id"])).all()
    out = []
    for g in rows:
        course = db.get(Course, g.course_id)
        out.append(
            {
                **grade_service.grade_to_dict(g),
                "course_code": course.course_code if course else None,
                "course_title": course.course_title if course else None,
            }
        )
    return out


@router.get("/student/grades/{course_id}")
def student_course_grade(
    course_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("student"))] = None,
):
    row = db.scalars(
        select(Grade).where(Grade.student_id == current["user_id"], Grade.course_id == course_id)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Grade not found")
    course = db.get(Course, course_id)
    return {
        **grade_service.grade_to_dict(row),
        "course_code": course.course_code if course else None,
        "course_title": course.course_title if course else None,
    }
