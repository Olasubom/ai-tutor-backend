from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.admin.models import Course, Department
from fastapi_app.auth.models import User
from fastapi_app.auth.utils import require_role
from fastapi_app.database import get_db
from fastapi_app.schemas.platform import LecturerEnsureRequest, SendResourceRequest
from fastapi_app.security import require_api_key
from fastapi_app.services import lecturer_service, notifications_service
from fastapi_app.services import lecturer_ai_service
from fastapi_app.services.memory_files import read_json
from agency.core.context import get_runtime

router = APIRouter(prefix="/lecturer", tags=["Lecturer"])


class LecturerChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    course_id: Optional[str] = None


def _user(db: Session, current: dict) -> User:
    user = db.get(User, current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/my-courses")
def get_lecturer_courses(
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
) -> list[dict]:
    """Courses a lecturer can upload materials for (by department)."""
    user = db.get(User, current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "admin" and not user.department:
        courses = db.scalars(select(Course).order_by(Course.course_code)).all()
    else:
        if not user.department:
            return []
        department = db.scalars(select(Department).where(Department.name == user.department)).first()
        if not department:
            return []
        courses = db.scalars(
            select(Course).where(Course.department_id == department.id).order_by(Course.course_code)
        ).all()

    return [
        {
            "id": c.id,
            "code": c.course_code,
            "title": c.course_title,
            "level": c.level,
            "semester": c.semester or "Both",
        }
        for c in courses
    ]


@router.post("/ensure/{lecturer_id}")
def ensure_lecturer(lecturer_id: str, payload: LecturerEnsureRequest, _: None = Depends(require_api_key)):
    return lecturer_service.ensure_lecturer_profile(
        lecturer_id,
        name=payload.name,
        department_id=payload.department_id,
        faculty_id=payload.faculty_id,
    )


@router.post("/send-resource")
def send_resource(payload: SendResourceRequest, _: None = Depends(require_api_key)):
    notifications_service.create_notification(
        payload.learner_id,
        type="new_resource",
        title="New resource from your lecturer",
        body=payload.note or payload.resource_url,
        action_url="/student/library",
    )
    return {"ok": True}


@router.get("/classes/{lecturer_id}")
def lecturer_classes(lecturer_id: str, _: None = Depends(require_api_key)):
    data = read_json(f"lecturers/{lecturer_id}.json", {"classes": []})
    return data.get("classes", [])


@router.get("/students/{lecturer_id}")
def lecturer_students(lecturer_id: str, _: None = Depends(require_api_key)):
    data = read_json(f"lecturers/{lecturer_id}.json", {"students": []})
    runtime = get_runtime()
    enriched = []
    for s in data.get("students", []):
        learner_id = s.get("learner_id") or s.get("id")
        profile = runtime.learner_memory.get_profile(learner_id) if learner_id else {}
        mastery = profile.get("knowledge_state_summary", {}).get("topic_mastery", {})
        enriched.append({**s, "topic_mastery": mastery})
    return enriched


@router.get("/dashboard")
def lecturer_dashboard(
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
) -> dict:
    user = _user(db, current)
    return {
        "name": user.name,
        "department": user.department or "",
        "email": user.email,
    }


@router.post("/ai-chat")
def lecturer_ai_chat(
    payload: LecturerChatRequest,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
) -> dict:
    user = _user(db, current)
    return lecturer_ai_service.lecturer_ai_chat(db, user, payload.message, payload.course_id)
