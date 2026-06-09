"""Learner structured memory files for onboarding and mastery."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi_app.services.memory_files import read_json, write_json


def init_structured_memory(user_id: str, name: str) -> None:
    write_json(
        f"structured/{user_id}.json",
        {
            "learner_id": user_id,
            "name": name,
            "topic_mastery": {},
            "knowledge_state_summary": {
                "weak_topics": [],
                "strong_topics": [],
                "overall_mastery_percentage": 0,
            },
            "total_study_hours": 0,
            "modules_completed": 0,
            "current_streak": 0,
            "onboarding_complete": False,
            "courses": [],
            "subject_ratings": [],
            "preferences": {},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def get_structured_memory(user_id: str) -> Dict[str, Any]:
    return read_json(f"structured/{user_id}.json", {})


def update_structured_memory(user_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    current = get_structured_memory(user_id)
    current.update(patch)
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_json(f"structured/{user_id}.json", current)
    return current


def onboarding_status(user_id: str) -> Dict[str, Any]:
    mem = get_structured_memory(user_id)
    complete = bool(mem.get("onboarding_complete"))
    missing: List[str] = []
    if not mem.get("college"):
        missing.append("college")
    if not mem.get("department"):
        missing.append("department")
    if not complete:
        missing.append("preferences")
    return {"is_complete": complete, "missing_steps": missing}
