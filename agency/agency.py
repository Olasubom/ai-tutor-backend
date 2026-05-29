"""
AI Tutor Agency — Agency Swarm wiring and communication flows.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from agency_swarm import Agency

from agency.agents.CoordinatorAgent import coordinator_agent
from agency.agents.KnowledgeTracingAgent import knowledge_tracing_agent
from agency.agents.RecommendationAgent import recommendation_agent
from agency.agents.TaskAgent import task_agent

_AGENCY_ROOT = Path(__file__).resolve().parent
_MANIFESTO = _AGENCY_ROOT / "agency_manifesto.md"


def _load_shared_instructions() -> str:
    if _MANIFESTO.exists():
        return _MANIFESTO.read_text(encoding="utf-8")
    return "You are part of the AI Tutor multi-agent system."


@lru_cache(maxsize=1)
def create_agency() -> Agency:
    """
    Build the Agency with Coordinator as the sole entry point.

    Communication flows (Coordinator can delegate to specialists):
      Coordinator -> KnowledgeTracingAgent
      Coordinator -> RecommendationAgent
      Coordinator -> TaskAgent
    """
    return Agency(
        coordinator_agent,
        communication_flows=[
            (coordinator_agent, knowledge_tracing_agent),
            (coordinator_agent, recommendation_agent),
            (coordinator_agent, task_agent),
        ],
        name="AI Tutor Agency",
        shared_instructions=_load_shared_instructions(),
    )


def get_agency() -> Agency:
    return create_agency()
