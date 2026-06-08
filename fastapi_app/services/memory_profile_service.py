from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List

from agency.core.context import get_runtime
from fastapi_app.services.memory_files import read_json, read_jsonl


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hour_bucket(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    return "evening"


def get_memory_profile(learner_id: str) -> dict:
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    topic_mastery = profile.get("topic_mastery", {})
    strengths = [t for t, s in topic_mastery.items() if float(s.get("p_l", 0)) > 0.75]
    weak_areas = [t for t, s in topic_mastery.items() if float(s.get("p_l", 0)) < 0.5]

    sessions = read_json(f"sessions/{learner_id}.json", [])
    events = read_jsonl(f"events/{learner_id}.jsonl")

    hour_counts: Counter = Counter()
    session_lengths: List[float] = []
    content_types: Counter = Counter()

    for s in sessions:
        started = s.get("started_at")
        ended = s.get("ended_at")
        if started:
            try:
                dt = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
                hour_counts[_hour_bucket(dt.hour)] += 1
            except ValueError:
                pass
        if started and ended:
            try:
                a = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
                b = datetime.fromisoformat(str(ended).replace("Z", "+00:00"))
                session_lengths.append(max((b - a).total_seconds() / 60, 1))
            except ValueError:
                pass

    for e in events:
        et = e.get("event_type")
        if et == "resource_click":
            content_types["video"] += 1
        elif et == "page_view":
            content_types["text"] += 1
        elif et in {"quiz_start", "quiz_submit"}:
            content_types["quiz"] += 1

    preferred_time = hour_counts.most_common(1)[0][0] if hour_counts else "evening"
    preferred_content = content_types.most_common(1)[0][0] if content_types else "video"
    avg_session = sum(session_lengths) / len(session_lengths) if session_lengths else 0.0

    weeks = max(len(sessions) / 4, 1) if sessions else 1
    sessions_per_week = len(sessions) / weeks

    summaries = [s.get("summary", "") for s in sessions[-3:] if s.get("summary")]

    last_active = profile.get("updated_at") or _now()
    for e in reversed(events):
        if e.get("timestamp"):
            last_active = e["timestamp"]
            break

    return {
        "strengths": strengths,
        "weak_areas": weak_areas,
        "study_habits": {
            "preferred_time": preferred_time,
            "avg_session_length_minutes": round(avg_session, 1),
            "sessions_per_week": round(sessions_per_week, 1),
            "preferred_content_type": preferred_content,
        },
        "recent_session_summaries": summaries,
        "total_interactions": len(events),
        "last_active": last_active,
    }
