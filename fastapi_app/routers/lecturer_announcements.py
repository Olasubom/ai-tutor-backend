"""Announcements and JWT-backed student notifications."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from fastapi_app.auth.models import User
from fastapi_app.auth.utils import require_role
from fastapi_app.database import get_db
from fastapi_app.schemas.lecturer_dashboard import AnnouncementCreate, AnnouncementUpdate
from fastapi_app.services import announcement_service
from fastapi_app.services import notifications_service

router = APIRouter(tags=["Announcements"])


@router.post("/lecturer/courses/{course_id}/announcements")
def post_announcement(
    course_id: str,
    payload: AnnouncementCreate,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    user = db.get(User, current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        row = announcement_service.create_announcement(
            db,
            user,
            course_id,
            title=payload.title,
            body=payload.body,
            is_pinned=payload.is_pinned,
        )
        return {
            "id": row.id,
            "title": row.title,
            "body": row.body,
            "created_at": row.created_at.isoformat(),
        }
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/lecturer/courses/{course_id}/announcements")
def list_course_announcements(
    course_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin", "student"))] = None,
):
    return announcement_service.list_announcements(db, course_id)


@router.put("/lecturer/announcements/{announcement_id}")
def edit_announcement(
    announcement_id: str,
    payload: AnnouncementUpdate,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    user = db.get(User, current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        row = announcement_service.update_announcement(
            db, user, announcement_id, payload.model_dump(exclude_none=True)
        )
        return {"id": row.id, "title": row.title, "body": row.body}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/lecturer/announcements/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    user = db.get(User, current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        announcement_service.delete_announcement(db, user, announcement_id)
        return {"message": "Announcement deleted"}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/student/notifications")
def student_notifications(
    unread_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("student"))] = None,
):
    return notifications_service.list_user_notifications(
        db, current["user_id"], unread_only=unread_only
    )


@router.get("/student/notifications/count")
def student_notification_count(
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("student"))] = None,
):
    return {"unread": notifications_service.count_unread(db, current["user_id"])}


@router.post("/student/notifications/{notification_id}/read")
def student_mark_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("student"))] = None,
):
    ok = notifications_service.mark_user_notification_read(db, current["user_id"], notification_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"ok": True}


@router.post("/student/notifications/read-all")
def student_mark_all_read(
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("student"))] = None,
):
    count = notifications_service.mark_all_user_notifications_read(db, current["user_id"])
    return {"marked": count}


@router.get("/student/courses/{course_id}/announcements")
def student_course_announcements(
    course_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("student"))] = None,
):
    return announcement_service.list_announcements(db, course_id)
