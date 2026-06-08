from __future__ import annotations

from fastapi import APIRouter, Depends

from fastapi_app.schemas.platform import LecturerEnsureRequest, SendResourceRequest
from fastapi_app.security import require_api_key
from fastapi_app.services import lecturer_service, notifications_service
from fastapi_app.services.memory_files import read_json
from agency.core.context import get_runtime

router = APIRouter(prefix="/lecturer", tags=["Lecturer"])


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
