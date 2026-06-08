from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from agency.core.context import get_runtime
from fastapi_app.services.memory_files import read_json, write_json


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def list_goals(learner_id: str) -> List[dict]:
    raw = read_json(f"goals/{learner_id}.json", [])
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    topic_mastery = profile.get("topic_mastery", {})
    now = datetime.now(timezone.utc)
    enriched = []
    for g in raw:
        topic = g.get("topic", "")
        state = topic_mastery.get(topic, {})
        current = float(state.get("p_l", 0.3))
        target = float(g.get("target_mastery", 0.8))
        try:
            target_dt = _parse_date(g.get("target_date", _now()))
        except ValueError:
            target_dt = now
        days_remaining = max(0, (target_dt.date() - now.date()).days)
        span = max(target - float(g.get("baseline_mastery", current)), 0.01)
        progress = min(100.0, max(0.0, ((current - float(g.get("baseline_mastery", current))) / span) * 100))
        on_track = current >= target or progress >= max(0, (1 - days_remaining / max(days_remaining + 7, 1)) * 100)
        enriched.append(
            {
                **g,
                "current_mastery": round(current, 4),
                "progress_percentage": round(progress, 1),
                "days_remaining": days_remaining,
                "on_track": on_track,
            }
        )
    return enriched


def create_goal(learner_id: str, topic: str, target_mastery: float, target_date: str) -> dict:
    goals = read_json(f"goals/{learner_id}.json", [])
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    current = float(profile.get("topic_mastery", {}).get(topic, {}).get("p_l", 0.3))
    goal = {
        "goal_id": str(uuid.uuid4()),
        "topic": topic,
        "target_mastery": target_mastery,
        "target_date": target_date,
        "baseline_mastery": current,
        "created_at": _now(),
    }
    goals.append(goal)
    write_json(f"goals/{learner_id}.json", goals)

    tasks = profile.get("tasks") or []
    tasks.append(
        {
            "id": str(uuid.uuid4()),
            "text": f"Study {topic} toward {int(target_mastery * 100)}% mastery goal",
            "status": "pending",
            "priority": "high",
            "course": topic,
            "due_date": target_date,
        }
    )
    runtime.learner_memory.upsert_profile(learner_id, {"tasks": tasks})
    return {**goal, "tasks_created": 1}


def delete_goal(learner_id: str, goal_id: str) -> bool:
    goals = read_json(f"goals/{learner_id}.json", [])
    filtered = [g for g in goals if g.get("goal_id") != goal_id]
    if len(filtered) == len(goals):
        return False
    write_json(f"goals/{learner_id}.json", filtered)
    return True
