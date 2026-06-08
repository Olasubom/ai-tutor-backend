from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from fastapi_app.security import require_api_key
from fastapi_app.services import notifications_service
from fastapi_app.services.memory_files import read_json, write_json

router = APIRouter(prefix="/notifications", tags=["Notifications"])

_DEFAULT_PREFS = {
    "study_reminders": True,
    "new_recommendation_alerts": True,
    "weekly_progress_email": False,
    "task_due_alerts": True,
    "mastery_drop_alerts": True,
}


@router.get("/preferences/{learner_id}")
def get_preferences(learner_id: str, _: None = Depends(require_api_key)):
    return read_json(f"notifications/prefs_{learner_id}.json", _DEFAULT_PREFS)


@router.patch("/preferences/{learner_id}")
def patch_preferences(learner_id: str, body: dict, _: None = Depends(require_api_key)):
    current = read_json(f"notifications/prefs_{learner_id}.json", _DEFAULT_PREFS)
    current.update(body)
    write_json(f"notifications/prefs_{learner_id}.json", current)
    return current


@router.get("/{learner_id}")
def list_notifications(learner_id: str, _: None = Depends(require_api_key)):
    return notifications_service.list_notifications(learner_id)


@router.post("/{learner_id}/read/{notification_id}")
def mark_read(learner_id: str, notification_id: str, _: None = Depends(require_api_key)):
    ok = notifications_service.mark_read(learner_id, notification_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"detail": "Notification not found", "code": "not_found"})
    return {"ok": True}


@router.post("/{learner_id}/read-all")
def mark_all_read(learner_id: str, _: None = Depends(require_api_key)):
    count = notifications_service.mark_all_read(learner_id)
    return {"marked": count}
