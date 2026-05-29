"""
Knowledge tracing specialist: BKT updates + mastery summaries.
"""

from __future__ import annotations

import logging
import os

from agency_swarm import Agent

from agency.core.agent_tools import get_current_mastery_summary, update_knowledge_from_events

logger = logging.getLogger(__name__)

_INSTRUCTIONS = """You are the KnowledgeTracingAgent.

## When performance events exist
- Call `update_knowledge_from_events` with a JSON list: `[{"topic": "...", "correct": true/false}]`.

## When no new events
- Call `get_current_mastery_summary`.

## Output
Return **structured JSON**:
- `knowledge_state_summary` (mastered / developing / weak, trend)
- `topic_mastery` (per-topic P(L) in [0,1])
- Brief diagnostic notes for the Coordinator

## Error handling
- Invalid JSON → ask for corrected events; do not guess mastery values.
- Never fabricate scores; only report tool outputs.
"""

try:
    knowledge_tracing_agent = Agent(
        name="KnowledgeTracingAgent",
        description="Tracks mastery over time using simplified BKT and trend summaries.",
        instructions=_INSTRUCTIONS,
        tools=[update_knowledge_from_events, get_current_mastery_summary],
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
    )
    logger.info("KnowledgeTracingAgent initialized")
except Exception:
    logger.exception("KnowledgeTracingAgent initialization failed")
    raise
