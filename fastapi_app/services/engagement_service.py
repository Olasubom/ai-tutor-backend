from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi_app.services.memory_files import append_jsonl, read_jsonl


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_engagement(learner_id: str, event_type: str, metadata: Optional[Dict[str, Any]] = None) -> dict:
    record = {
        "timestamp": _now(),
        "event_type": event_type,
        "metadata": metadata or {},
    }
    append_jsonl(f"events/{learner_id}.jsonl", record)
    return record


def get_heatmap(learner_id: str, period: str = "all") -> List[dict]:
    events = read_jsonl(f"events/{learner_id}.jsonl")
    now = datetime.now(timezone.utc)
    if period == "7d":
        cutoff = now - timedelta(days=7)
    elif period == "30d":
        cutoff = now - timedelta(days=30)
    else:
        cutoff = now - timedelta(days=365)

    counts: Dict[str, int] = defaultdict(int)
    for e in events:
        ts = e.get("timestamp")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt < cutoff:
            continue
        counts[dt.date().isoformat()] += 1

    if period == "7d":
        days = 7
    elif period == "30d":
        days = 30
    else:
        days = 365

    result = []
    for i in range(days - 1, -1, -1):
        d = (now - timedelta(days=i)).date().isoformat()
        result.append({"date": d, "count": counts.get(d, 0)})
    return result


def get_daily_metrics(learner_id: str, period: str = "7d") -> List[dict]:
    """Study time proxy and questions answered per day from events."""
    events = read_jsonl(f"events/{learner_id}.jsonl")
    now = datetime.now(timezone.utc)
    days = 7 if period == "7d" else 30 if period == "30d" else 365
    cutoff = now - timedelta(days=days)

    buckets: Dict[str, Dict[str, float]] = defaultdict(lambda: {"study_time": 0.0, "questions_answered": 0.0})
    for e in events:
        ts = e.get("timestamp")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt < cutoff:
            continue
        key = dt.date().isoformat()
        et = e.get("event_type")
        meta = e.get("metadata") or {}
        if et in {"page_view", "resource_click", "chat_message"}:
            buckets[key]["study_time"] += float(meta.get("minutes", 5))
        if et in {"quiz_start", "quiz_submit"}:
            buckets[key]["questions_answered"] += float(meta.get("questions", 1))

    result = []
    for i in range(days - 1, -1, -1):
        d = (now - timedelta(days=i)).date().isoformat()
        b = buckets.get(d, {"study_time": 0.0, "questions_answered": 0.0})
        result.append({"date": d, **b})
    return result
