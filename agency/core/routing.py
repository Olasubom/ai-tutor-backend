"""
Keyword-based routing hints for CoordinatorAgent.

These hints are injected into agency runs to reduce mis-routing and hallucinated delegation.
"""

from __future__ import annotations

import re
from typing import List, Tuple

# (pattern, primary_agent, optional_secondary_agents)
_ROUTES: List[Tuple[re.Pattern[str], str, List[str]]] = [
    (
        re.compile(
            r"\b(study plan|schedule|deadline|calendar|plan my week|homework|due date|timetable)\b",
            re.I,
        ),
        "TaskAgent",
        ["RecommendationAgent"],
    ),
    (
        re.compile(
            r"\b(recommend|what should i study|next lesson|suggest|content|learn next|practice)\b",
            re.I,
        ),
        "RecommendationAgent",
        ["KnowledgeTracingAgent"],
    ),
    (
        re.compile(
            r"\b(how am i doing|progress|mastery|weak topics?|my score|performance|am i improving)\b",
            re.I,
        ),
        "KnowledgeTracingAgent",
        [],
    ),
    (
        re.compile(r"\b(quiz|results?|got .* wrong|practice score|assessment)\b", re.I),
        "KnowledgeTracingAgent",
        ["RecommendationAgent"],
    ),
]


def detect_routing_hint(message: str, has_events: bool = False) -> str:
    """
    Return additional instructions for the Coordinator based on message content.

    If multiple patterns match, KnowledgeTracing takes priority when events exist.
    """
    message = message or ""
    matched: List[Tuple[str, List[str]]] = []

    for pattern, primary, secondary in _ROUTES:
        if pattern.search(message):
            matched.append((primary, secondary))

    if has_events and not any(m[0] == "KnowledgeTracingAgent" for m in matched):
        matched.insert(0, ("KnowledgeTracingAgent", ["RecommendationAgent"]))

    if not matched:
        return (
            "No strong routing keyword detected. Retrieve memory, then decide whether "
            "RecommendationAgent, TaskAgent, or KnowledgeTracingAgent is needed."
        )

    lines = ["Routing hints (follow in order):"]
    seen = set()
    order = 0
    for primary, secondary in matched:
        for agent in [primary, *secondary]:
            if agent in seen:
                continue
            seen.add(agent)
            order += 1
            lines.append(f"{order}. Delegate to {agent} via send_message.")

    return "\n".join(lines)
