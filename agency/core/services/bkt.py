from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from agency.core.tools.utils import clamp


@dataclass(frozen=True)
class BKTParams:
    p_l0: float = 0.2
    p_t: float = 0.3
    p_s: float = 0.1
    p_g: float = 0.2


def default_skill_state(params: BKTParams | None = None) -> Dict[str, float]:
    p = params or BKTParams()
    return {
        "p_l0": p.p_l0,
        "p_t": p.p_t,
        "p_s": p.p_s,
        "p_g": p.p_g,
        "p_l": p.p_l0,
    }


def update_bkt(p_l: float, correct: bool, params: BKTParams) -> float:
    """Single observation BKT update; returns new P(L)."""
    if correct:
        num = p_l * (1.0 - params.p_s)
        den = num + (1.0 - p_l) * params.p_g
    else:
        num = p_l * params.p_s
        den = num + (1.0 - p_l) * (1.0 - params.p_g)
    p_l_given_obs = num / den if den else p_l
    p_l_new = p_l_given_obs + (1.0 - p_l_given_obs) * params.p_t
    return clamp(p_l_new)


def apply_events(
    topic_mastery: Dict[str, Dict[str, Any]],
    events: List[Dict[str, Any]],
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Apply performance events and return updated mastery + summary."""
    history: List[Dict[str, Any]] = []
    for event in events:
        topic = str(event.get("topic") or event.get("skill_id") or "").strip()
        if not topic:
            continue
        correct = bool(event.get("correct", False))
        state = topic_mastery.get(topic) or default_skill_state()
        params = BKTParams(
            p_l0=float(state.get("p_l0", 0.2)),
            p_t=float(state.get("p_t", 0.3)),
            p_s=float(state.get("p_s", 0.1)),
            p_g=float(state.get("p_g", 0.2)),
        )
        p_l = float(state.get("p_l", params.p_l0))
        p_l = update_bkt(p_l, correct, params)
        topic_mastery[topic] = {
            **state,
            "p_l": p_l,
            "attempts": int(state.get("attempts", 0)) + 1,
            "correct_count": int(state.get("correct_count", 0)) + (1 if correct else 0),
        }
        history.append({"topic": topic, "correct": correct})

    summary = summarize_mastery(topic_mastery, recent=history)
    return topic_mastery, summary


def summarize_mastery(
    topic_mastery: Dict[str, Dict[str, Any]],
    recent: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    mastered: List[str] = []
    developing: List[str] = []
    weak: List[str] = []
    topic_scores: Dict[str, float] = {}

    for topic, state in topic_mastery.items():
        p_l = float(state.get("p_l", 0.0))
        topic_scores[topic] = p_l
        if p_l >= 0.85:
            mastered.append(topic)
        elif p_l >= 0.55:
            developing.append(topic)
        else:
            weak.append(topic)

    trend = "stable"
    if recent:
        correct = sum(1 for e in recent if e.get("correct"))
        acc = correct / len(recent)
        if acc >= 0.75:
            trend = "improving"
        elif acc <= 0.4:
            trend = "declining"

    return {
        "mastered_topics": sorted(mastered),
        "developing_topics": sorted(developing),
        "weak_topics": sorted(weak),
        "topic_mastery": topic_scores,
        "trend": trend,
    }
