from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from agency.core.context import get_runtime
from agency.core.services.bkt import apply_events, default_skill_state
from fastapi_app.services.memory_files import read_jsonl


def get_knowledge(learner_id: str) -> dict:
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    topic_mastery = profile.get("topic_mastery", {})
    subjects = [
        {
            "topic": topic,
            "mastery": round(float(state.get("p_l", 0)) * 100),
            "attempts": int(state.get("attempts", 0)),
        }
        for topic, state in topic_mastery.items()
    ]
    return {
        "learner_id": learner_id,
        "subjects": sorted(subjects, key=lambda s: s["mastery"]),
        "summary": profile.get("knowledge_state_summary", {}),
    }


def patch_topic(learner_id: str, topic: str, proficiency: str) -> dict:
    mapping = {
        "no_knowledge": 0.15,
        "familiar": 0.45,
        "comfortable": 0.65,
        "proficient": 0.85,
    }
    p_l = mapping.get(proficiency, 0.45)
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    topic_mastery = profile.get("topic_mastery", {})
    state = topic_mastery.get(topic) or default_skill_state()
    state["p_l"] = p_l
    topic_mastery[topic] = state
    runtime.learner_memory.upsert_profile(learner_id, {"topic_mastery": topic_mastery})
    return {"topic": topic, "mastery": p_l}


def mastery_trajectory(learner_id: str) -> List[dict]:
    events = read_jsonl(f"events/{learner_id}.jsonl")
    by_day: Dict[str, List[float]] = defaultdict(list)
    for e in events:
        if e.get("mastery_after") is not None:
            ts = str(e.get("timestamp", ""))[:10]
            by_day[ts].append(float(e["mastery_after"]))
        elif e.get("event_type") == "quiz_submit" and e.get("percentage") is not None:
            ts = str(e.get("timestamp", ""))[:10]
            by_day[ts].append(float(e["percentage"]) / 100)

    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    topic_mastery = profile.get("topic_mastery", {})
    current = (
        sum(float(s.get("p_l", 0)) for s in topic_mastery.values()) / len(topic_mastery)
        if topic_mastery
        else 0.3
    )

    now = datetime.now(timezone.utc)
    result = []
    rolling = current
    for i in range(29, -1, -1):
        d = (now - timedelta(days=i)).date().isoformat()
        if d in by_day:
            rolling = sum(by_day[d]) / len(by_day[d])
        result.append({"date": d, "overall_mastery": round(rolling, 4)})
    return result


def enrich_profile(learner_id: str, profile: dict) -> dict:
    """Add computed dashboard fields to profile."""
    events = read_jsonl(f"events/{learner_id}.jsonl")
    topic_mastery = profile.get("topic_mastery", {})
    overall = (
        sum(float(s.get("p_l", 0)) for s in topic_mastery.values()) / len(topic_mastery)
        if topic_mastery
        else 0.0
    )

    study_minutes = 0.0
    days_active = set()
    for e in events:
        ts = str(e.get("timestamp", ""))[:10]
        if ts:
            days_active.add(ts)
        meta = e.get("metadata") or {}
        if e.get("event_type") in {"page_view", "chat_message", "resource_click"}:
            study_minutes += float(meta.get("minutes", 5))

    streak = 0
    today = datetime.now(timezone.utc).date()
    for i in range(365):
        d = (today - timedelta(days=i)).isoformat()
        if d in days_active:
            streak += 1
        elif i > 0:
            break

    modules = sum(1 for s in topic_mastery.values() if float(s.get("p_l", 0)) >= 0.85)

    return {
        **profile,
        "total_study_hours": round(study_minutes / 60, 1),
        "modules_completed": modules,
        "current_streak": streak,
        "overall_mastery_percentage": round(overall * 100),
    }
