from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from agency.core.context import get_runtime
from fastapi_app.services.memory_files import read_json, read_jsonl


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _severity(factors: List[str]) -> str:
    red = sum(1 for f in factors if "mastery" in f.lower() or "quiz" in f.lower())
    if red >= 2 or len(factors) >= 3:
        return "high"
    if len(factors) >= 2:
        return "medium"
    return "low"


def list_at_risk(lecturer_id: str) -> List[dict]:
    lecturer = read_json(f"lecturers/{lecturer_id}.json", {"students": []})
    dismissed = {
        d.get("learner_id")
        for d in read_json(f"at_risk_dismissed/{lecturer_id}.json", [])
    }
    students = lecturer.get("students") or []
    runtime = get_runtime()
    now = datetime.now(timezone.utc)
    alerts: List[dict] = []

    for student in students:
        learner_id = student.get("learner_id") or student.get("id")
        if not learner_id or learner_id in dismissed:
            continue

        factors: List[str] = []
        profile = runtime.learner_memory.get_profile(learner_id)
        events = read_jsonl(f"events/{learner_id}.jsonl")

        last_active = None
        for e in reversed(events):
            ts = e.get("timestamp")
            if ts:
                try:
                    last_active = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                    break
                except ValueError:
                    pass
        if last_active and (now - last_active).days >= 5:
            factors.append(f"Inactive {(now - last_active).days} days")

        quiz_events = [e for e in events if e.get("event_type") == "quiz_submit" or e.get("quiz_id")]
        recent_quizzes = quiz_events[-3:]
        if len(recent_quizzes) >= 3:
            avg_pct = sum(float(e.get("percentage", 0)) for e in recent_quizzes) / len(recent_quizzes)
            if avg_pct < 50:
                factors.append("Low quiz accuracy")

        topic_mastery = profile.get("topic_mastery", {})
        for topic, state in topic_mastery.items():
            p_l = float(state.get("p_l", 0))
            if p_l < 0.35:
                factors.append(f"Low mastery in {topic}")

        tasks = profile.get("tasks") or []
        overdue = 0
        for t in tasks:
            if t.get("status") == "completed":
                continue
            due = t.get("due_date")
            if not due:
                continue
            try:
                due_dt = datetime.fromisoformat(str(due).replace("Z", "+00:00"))
                if due_dt < now:
                    overdue += 1
            except ValueError:
                pass
        if overdue > 2:
            factors.append(f"{overdue} tasks overdue")

        if not factors:
            continue

        alerts.append(
            {
                "learner_id": learner_id,
                "name": student.get("name", learner_id),
                "department": student.get("department", "General"),
                "level": student.get("level", "100"),
                "risk_factors": factors,
                "severity": _severity(factors),
                "last_active": last_active.isoformat() if last_active else _now(),
                "suggested_action": (
                    f"Schedule a check-in with {student.get('name', 'this student')} "
                    f"and assign targeted review for weak topics."
                ),
            }
        )

    return alerts


def dismiss_alert(lecturer_id: str, learner_id: str) -> None:
    items = read_json(f"at_risk_dismissed/{lecturer_id}.json", [])
    items.append({"learner_id": learner_id, "dismissed_at": _now()})
    from fastapi_app.services.memory_files import write_json

    write_json(f"at_risk_dismissed/{lecturer_id}.json", items)
