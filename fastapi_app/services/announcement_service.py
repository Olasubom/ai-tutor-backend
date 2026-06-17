"""Announcement CRUD for lecturer courses."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.admin.models import Course
from fastapi_app.auth.models import User
from fastapi_app.models.lecturer_dashboard import Announcement
from fastapi_app.services.lecturer_course_service import assert_lecturer_owns_course
from fastapi_app.services import notifications_service


def create_announcement(
    db: Session,
    user: User,
    course_id: str,
    *,
    title: str,
    body: str,
    is_pinned: bool = False,
) -> Announcement:
    course = db.get(Course, course_id)
    if not course:
        raise ValueError("Course not found")
    assert_lecturer_owns_course(db, user, course)
    row = Announcement(
        course_id=course_id,
        lecturer_id=user.id,
        title=title.strip(),
        body=body.strip(),
        is_pinned=is_pinned,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    notifications_service.notify_enrolled_students(
        db,
        course_id,
        title=title,
        message=body,
        notification_type="announcement",
        announcement_id=row.id,
    )
    return row


def list_announcements(db: Session, course_id: str) -> List[dict]:
    rows = db.scalars(
        select(Announcement)
        .where(Announcement.course_id == course_id)
        .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
    ).all()
    return [
        {
            "id": r.id,
            "course_id": r.course_id,
            "lecturer_id": r.lecturer_id,
            "title": r.title,
            "body": r.body,
            "is_pinned": r.is_pinned,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


def update_announcement(db: Session, user: User, announcement_id: str, patch: dict) -> Announcement:
    row = db.get(Announcement, announcement_id)
    if not row:
        raise ValueError("Announcement not found")
    course = db.get(Course, row.course_id)
    assert course is not None
    assert_lecturer_owns_course(db, user, course)
    if "title" in patch:
        row.title = str(patch["title"]).strip()
    if "body" in patch:
        row.body = str(patch["body"]).strip()
    if "is_pinned" in patch:
        row.is_pinned = bool(patch["is_pinned"])
    db.commit()
    db.refresh(row)
    return row


def delete_announcement(db: Session, user: User, announcement_id: str) -> None:
    row = db.get(Announcement, announcement_id)
    if not row:
        raise ValueError("Announcement not found")
    course = db.get(Course, row.course_id)
    assert course is not None
    assert_lecturer_owns_course(db, user, course)
    db.delete(row)
    db.commit()
