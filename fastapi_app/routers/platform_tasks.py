from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from fastapi_app.schemas.platform import TaskCreateRequest
from fastapi_app.security import require_api_key
from fastapi_app.services import tasks_service

router = APIRouter(prefix="/tutor/tasks", tags=["Tasks"])


@router.get("/{learner_id}")
def list_tasks(learner_id: str, _: None = Depends(require_api_key)):
    try:
        tasks_service.check_due_notifications(learner_id)
    except Exception:
        pass  # notification check must not block task listing
    return tasks_service.list_tasks(learner_id)


@router.post("/{learner_id}")
def create_task(learner_id: str, payload: TaskCreateRequest, _: None = Depends(require_api_key)):
    return tasks_service.create_task(
        learner_id,
        text=payload.text,
        due_date=payload.due_date,
        priority=payload.priority,
        course=payload.course,
    )


@router.patch("/{learner_id}/{task_id}/complete")
def complete_task(learner_id: str, task_id: str, _: None = Depends(require_api_key)):
    task = tasks_service.complete_task(learner_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail={"detail": "Task not found", "code": "not_found"})
    return task


@router.delete("/{learner_id}/{task_id}")
def delete_task(learner_id: str, task_id: str, _: None = Depends(require_api_key)):
    ok = tasks_service.delete_task(learner_id, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"detail": "Task not found", "code": "not_found"})
    return {"ok": True}
