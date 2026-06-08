from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, List

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
