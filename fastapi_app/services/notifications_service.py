from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi_app.models.lecturer_dashboard import Announcement, CourseEnrollment, UserNotification
from fastapi_app.services.memory_files import cap_list, read_json, write_json


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_notifications(learner_id: str) -> List[dict]:
    return read_json(f"notifications/{learner_id}.json", [])


def create_notification(
    learner_id: str,
    *,
    type: str,
    title: str,
    body: str,
    action_url: str,
) -> dict:
    items = list_notifications(learner_id)
    note = {
        "notification_id": str(uuid.uuid4()),
        "type": type,
        "title": title,
        "body": body,
        "is_read": False,
        "created_at": _now(),
        "action_url": action_url,
    }
    items.append(note)
    write_json(f"notifications/{learner_id}.json", cap_list(items, 50))
    return note


def create_user_notification(
    db: Session,
    user_id: str,
    *,
    title: str,
    message: str,
    notification_type: str = "announcement",
    announcement_id: Optional[str] = None,
) -> UserNotification:
    """Persist notification in DB and mirror to legacy JSON file."""
    row = UserNotification(
        user_id=user_id,
        announcement_id=announcement_id,
        title=title,
        message=message,
        notification_type=notification_type,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    create_notification(
        user_id,
        type=notification_type,
        title=title,
        body=message,
        action_url="/student/notifications",
    )
    return row


def notify_enrolled_students(
    db: Session,
    course_id: str,
    *,
    title: str,
    message: str,
    notification_type: str,
    announcement_id: Optional[str] = None,
) -> int:
    rows = db.scalars(
        select(CourseEnrollment.student_id).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.status == "active",
        )
    ).all()
    count = 0
    for student_id in rows:
        create_user_notification(
            db,
            student_id,
            title=title,
            message=message,
            notification_type=notification_type,
            announcement_id=announcement_id,
        )
        count += 1
    return count


def list_user_notifications(db: Session, user_id: str, *, unread_only: bool = False) -> List[dict]:
    q = select(UserNotification).where(UserNotification.user_id == user_id)
    if unread_only:
        q = q.where(UserNotification.is_read == False)  # noqa: E712
    rows = db.scalars(q.order_by(UserNotification.created_at.desc())).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "message": r.message,
            "is_read": r.is_read,
            "notification_type": r.notification_type,
            "announcement_id": r.announcement_id,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


def count_unread(db: Session, user_id: str) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(UserNotification)
            .where(UserNotification.user_id == user_id, UserNotification.is_read == False)  # noqa: E712
        )
        or 0
    )


def mark_user_notification_read(db: Session, user_id: str, notification_id: str) -> bool:
    row = db.get(UserNotification, notification_id)
    if not row or row.user_id != user_id:
        return False
    row.is_read = True
    db.commit()
    mark_read(user_id, notification_id)
    return True


def mark_all_user_notifications_read(db: Session, user_id: str) -> int:
    rows = db.scalars(
        select(UserNotification).where(
            UserNotification.user_id == user_id,
            UserNotification.is_read == False,  # noqa: E712
        )
    ).all()
    for row in rows:
        row.is_read = True
    db.commit()
    return mark_all_read(user_id)


def mark_read(learner_id: str, notification_id: str) -> bool:
    items = list_notifications(learner_id)
    found = False
    for n in items:
        if n.get("notification_id") == notification_id:
            n["is_read"] = True
            found = True
    if found:
        write_json(f"notifications/{learner_id}.json", items)
    return found


def mark_all_read(learner_id: str) -> int:
    items = list_notifications(learner_id)
    count = 0
    for n in items:
        if not n.get("is_read"):
            n["is_read"] = True
            count += 1
    write_json(f"notifications/{learner_id}.json", items)
    return count
