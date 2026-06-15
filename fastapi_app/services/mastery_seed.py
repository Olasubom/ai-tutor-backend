"""Shared proficiency → initial mastery mapping (not BKT)."""

from __future__ import annotations

from typing import Any, Dict

from agency.core.services.bkt import default_skill_state, summarize_mastery

PROFICIENCY_P_L: Dict[str, float] = {
    "no_knowledge": 0.12,
    "none": 0.12,
    "familiar": 0.35,
    "comfortable": 0.55,
    "proficient": 0.78,
}


def seed_topic_mastery_from_assessments(
    topic_mastery: Dict[str, Dict[str, Any]],
    assessments: list[dict],
) -> tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Set initial p_l from self-assessment without simulating quiz events."""
    for assessment in assessments:
        topic = str(assessment.get("topic") or "").strip()
        if not topic:
            continue
        prof = str(assessment.get("proficiency") or "familiar").lower()
        p_l = PROFICIENCY_P_L.get(prof, 0.35)
        state = default_skill_state()
        state["p_l"] = p_l
        state["attempts"] = 0
        state["correct_count"] = 0
        state["seeded_from"] = prof
        topic_mastery[topic] = state

    summary = summarize_mastery(topic_mastery)
    summary["overall_mastery_percentage"] = round(
        sum(float(s.get("p_l", 0)) for s in topic_mastery.values()) / len(topic_mastery) * 100
    ) if topic_mastery else 0
    return topic_mastery, summary
