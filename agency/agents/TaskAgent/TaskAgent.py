"""
Study planning and task scheduling agent.
"""

from __future__ import annotations

import logging
import os

from agency_swarm import Agent

from agency.core.agent_tools import create_study_plan, list_learner_tasks, retrieve_learner_memory

logger = logging.getLogger(__name__)

_INSTRUCTIONS = """You are the TaskAgent.

## Steps
1. Call `retrieve_learner_memory` for deadlines, constraints, and preferences.
2. Call `list_learner_tasks` to avoid duplicate work.
3. Call `create_study_plan` with the learner's time budget (default 60 minutes).
4. Return **structured JSON**: `study_plan` and `tasks`.

## Adaptivity
- If learner is struggling (weak topics / declining trend), shorter sessions + fundamentals.
- If improving, add spaced review and slightly harder practice.

## Error handling
- On tool failure, return `{"error": "..."}` with a helpful message.
- Do not invent due dates or tasks not created by tools.
"""

try:
    task_agent = Agent(
        name="TaskAgent",
        description="Creates study schedules and manages academic tasks.",
        instructions=_INSTRUCTIONS,
        tools=[retrieve_learner_memory, list_learner_tasks, create_study_plan],
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
    )
    logger.info("TaskAgent initialized")
except Exception:
    logger.exception("TaskAgent initialization failed")
    raise
