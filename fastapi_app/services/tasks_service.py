from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agency.core.context import get_runtime
from fastapi_app.services.engagement_service import record_engagement
from fastapi_app.services import notifications_service
from fastapi_app.services.memory_files import append_jsonl


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_tasks(learner_id: str) -> List[dict]:
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    return profile.get("tasks") or []


def create_task(
    learner_id: str,
    *,
    text: str,
    due_date: str,
    priority: str = "medium",
    course: str = "General",
) -> dict:
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    tasks = list(profile.get("tasks") or [])
    task = {
        "id": str(uuid.uuid4()),
        "task_id": str(uuid.uuid4()),
        "text": text,
        "title": text,
        "status": "pending",
        "priority": priority,
        "course": course,
        "due_date": due_date,
    }
    tasks.append(task)
    runtime.learner_memory.upsert_profile(learner_id, {"tasks": tasks})
    record_engagement(learner_id, "task_create", {"task_id": task["id"]})
    return task


def complete_task(learner_id: str, task_id: str) -> Optional[dict]:
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    tasks = list(profile.get("tasks") or [])
    updated = None
    for t in tasks:
        if t.get("id") == task_id or t.get("task_id") == task_id:
            t["status"] = "completed"
            updated = t
            break
    if not updated:
        return None
    runtime.learner_memory.upsert_profile(learner_id, {"tasks": tasks})
    append_jsonl(
        f"events/{learner_id}.jsonl",
        {"timestamp": _now(), "event_type": "task_complete", "task_id": task_id},
    )
    record_engagement(learner_id, "task_complete", {"task_id": task_id})
    return updated


def delete_task(learner_id: str, task_id: str) -> bool:
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    tasks = list(profile.get("tasks") or [])
    filtered = [t for t in tasks if t.get("id") != task_id and t.get("task_id") != task_id]
    if len(filtered) == len(tasks):
        return False
    runtime.learner_memory.upsert_profile(learner_id, {"tasks": filtered})
    return True


def check_due_notifications(learner_id: str) -> int:
    """Create task_due notifications for tasks due within 24 hours."""
    tasks = list_tasks(learner_id)
    now = datetime.now(timezone.utc)
    created = 0
    for t in tasks:
        if t.get("status") == "completed":
            continue
        due = t.get("due_date")
        if not due:
            continue
        try:
            due_dt = datetime.fromisoformat(str(due).replace("Z", "+00:00"))
        except ValueError:
            continue
        hours = (due_dt - now).total_seconds() / 3600
        if 0 < hours <= 24:
            notifications_service.create_notification(
                learner_id,
                type="task_due",
                title="Task due soon",
                body=str(t.get("text") or t.get("title", "Task")),
                action_url="/student/tasks",
            )
            created += 1
    return created
