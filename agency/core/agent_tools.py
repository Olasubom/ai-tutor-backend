"""
Shared function tools for all AI Tutor agents.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from agency_swarm import RunContextWrapper, function_tool
from pydantic import BaseModel, Field

from agency.core.context import get_runtime
from agency.core.services.bkt import apply_events, summarize_mastery
from agency.core.services.recommender import hybrid_recommend

logger = logging.getLogger(__name__)


def _learner_id(ctx: RunContextWrapper) -> str:
    learner_id = ctx.context.get("learner_id")
    if not learner_id:
        raise ValueError("learner_id missing from agency user_context")
    return str(learner_id)


def _profile(ctx: RunContextWrapper) -> Dict[str, Any]:
    runtime = get_runtime()
    return runtime.learner_memory.get_profile(_learner_id(ctx))


# ---------------------------------------------------------------------------
# Memory tools
# ---------------------------------------------------------------------------


class RetrieveMemoryArgs(BaseModel):
    query: str = Field(..., description="Semantic query for long-term memory retrieval")
    top_k: int = Field(8, description="Number of vector memories to retrieve")


@function_tool
async def retrieve_learner_memory(ctx: RunContextWrapper, args: RetrieveMemoryArgs) -> str:
    """Retrieve short-term history, structured profile, and semantic vector memories."""
    try:
        runtime = get_runtime()
        learner_id = _learner_id(ctx)
        bundle = runtime.learner_memory.get_relevant_memory(
            learner_id, query=args.query, k=min(args.top_k, 10)
        )
        bundle["full_profile"] = runtime.learner_memory.get_profile(learner_id)
        return json.dumps(bundle, ensure_ascii=False)
    except Exception as exc:
        logger.exception("retrieve_learner_memory_failed")
        return json.dumps({"error": str(exc), "vector_memories": [], "recent_turns": []})


class WriteMemoryArgs(BaseModel):
    content: str = Field(..., description="Atomic memory fact to store")
    memory_type: str = Field(..., description="preference|performance|weakness|goal|constraint|milestone|misconception|plan")
    topic_tags: List[str] = Field(default_factory=list)
    source: str = Field("agent", description="Agent name writing this memory")


@function_tool
async def write_learner_memory(ctx: RunContextWrapper, args: WriteMemoryArgs) -> str:
    """Persist a durable learner memory fact into vector long-term memory."""
    try:
        runtime = get_runtime()
        learner_id = _learner_id(ctx)
        rec = runtime.vector_store.add_memory(
            learner_id=learner_id,
            content=args.content,
            memory_type=args.memory_type,
            topic_tags=args.topic_tags,
            source=args.source,
        )
        return json.dumps({"stored": True, "memory_id": rec.id}, ensure_ascii=False)
    except Exception as exc:
        logger.exception("write_learner_memory_failed")
        return json.dumps({"stored": False, "error": str(exc)})


# ---------------------------------------------------------------------------
# Knowledge tracing tools
# ---------------------------------------------------------------------------


class PerformanceEvent(BaseModel):
    topic: str = Field(..., description="Skill/topic identifier")
    correct: bool = Field(..., description="Whether the learner answered correctly")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpdateKnowledgeArgs(BaseModel):
    events_json: str = Field(..., description="JSON list of performance events")


@function_tool
async def update_knowledge_from_events(ctx: RunContextWrapper, args: UpdateKnowledgeArgs) -> str:
    """Update per-topic mastery using simplified BKT from new performance events."""
    try:
        runtime = get_runtime()
        learner_id = _learner_id(ctx)
        raw_events = json.loads(args.events_json)
        events = [PerformanceEvent.model_validate(e).model_dump() for e in raw_events]
        runtime.learner_memory.update_learner_profile(learner_id, events)

        profile = runtime.learner_memory.get_profile(learner_id)
        topic_mastery: Dict[str, Dict[str, Any]] = profile.get("topic_mastery", {})
        topic_mastery, summary = apply_events(topic_mastery, events)

        runtime.learner_memory.upsert_profile(
            learner_id,
            {"topic_mastery": topic_mastery, "knowledge_state_summary": summary},
        )
        if summary.get("weak_topics"):
            for topic in summary["weak_topics"][:3]:
                try:
                    runtime.vector_store.add_memory(
                        learner_id=learner_id,
                        content=f"Learner is struggling with {topic}.",
                        memory_type="weakness",
                        topic_tags=[topic],
                        source="KnowledgeTracingAgent",
                    )
                except Exception:
                    logger.warning("weakness_vector_write_skipped", extra={"topic": topic})
        return json.dumps(
            {"knowledge_state_summary": summary, "topic_mastery": topic_mastery},
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("update_knowledge_from_events_failed")
        return json.dumps({"error": str(exc)})


@function_tool
async def get_current_mastery_summary(ctx: RunContextWrapper) -> str:
    """Return current mastery bands (mastered/developing/weak) and topic scores."""
    try:
        profile = _profile(ctx)
        topic_mastery = profile.get("topic_mastery", {})
        summary = profile.get("knowledge_state_summary") or summarize_mastery(topic_mastery)
        return json.dumps(summary, ensure_ascii=False)
    except Exception as exc:
        logger.exception("get_current_mastery_summary_failed")
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Recommendation tools
# ---------------------------------------------------------------------------


class RecommendArgs(BaseModel):
    query: str = Field("what should I study next", description="Learner intent for retrieval context")
    limit: int = Field(6, description="Max recommendations")


@function_tool
async def generate_recommendations(ctx: RunContextWrapper, args: RecommendArgs) -> str:
    """Hybrid content+collaborative+memory recommendations and adaptive path."""
    try:
        runtime = get_runtime()
        learner_id = _learner_id(ctx)
        mem = runtime.learner_memory.get_relevant_memory(learner_id, args.query, k=8)
        profile = runtime.learner_memory.get_profile(learner_id)
        summary = profile.get("knowledge_state_summary", mem.get("profile_highlights", {}))
        weak_topics = summary.get("weak_topics", []) if isinstance(summary, dict) else []
        preferences = profile.get("preferences", {})
        preferred_modalities = (
            mem.get("profile_highlights", {}).get("preferred_modalities", [])
            if isinstance(mem.get("profile_highlights"), dict)
            else []
        )
        preference_terms = (
            [f"{k}:{v}" for k, v in preferences.items()]
            if isinstance(preferences, dict)
            else preferences if isinstance(preferences, list) else []
        )
        memory_snippets = [m["content"] for m in mem.get("vector_memories", [])]

        ranked, adaptive_path = hybrid_recommend(
            catalog=runtime.catalog,
            weak_topics=weak_topics,
            preferences=preference_terms if isinstance(preference_terms, list) else [],
            memory_snippets=memory_snippets,
            preferred_modalities=preferred_modalities if isinstance(preferred_modalities, list) else [],
            limit=args.limit,
        )
        recommendations = [
            {
                "item_id": r.item_id,
                "topic": r.payload.get("topic"),
                "title": r.payload.get("title"),
                "description": r.payload.get("description"),
                "difficulty": r.payload.get("difficulty"),
                "duration_minutes": r.payload.get("duration_minutes"),
                "topics": r.payload.get("topics", []),
                "tags": r.payload.get("tags", []),
                "modality": r.payload.get("modality"),
                "bloom_level": r.payload.get("bloom_level"),
                "source_type": r.payload.get("source_type"),
                "provider": r.payload.get("provider"),
                "source_url": r.payload.get("source_url"),
                "score": round(r.score, 3),
                "reasons": r.reasons,
            }
            for r in ranked
        ]
        payload = {"recommendations": recommendations, "adaptive_path": adaptive_path}
        runtime.learner_memory.upsert_profile(learner_id, {"last_recommendations": payload})
        return json.dumps(payload, ensure_ascii=False)
    except Exception as exc:
        logger.exception("generate_recommendations_failed")
        return json.dumps({"error": str(exc), "recommendations": [], "adaptive_path": []})


# ---------------------------------------------------------------------------
# Task / planning tools
# ---------------------------------------------------------------------------


class StudyPlanArgs(BaseModel):
    time_budget_minutes: int = Field(60, description="Available study time for the session")
    recommendations_json: str = Field("", description="Optional JSON recommendations payload")


@function_tool
async def create_study_plan(ctx: RunContextWrapper, args: StudyPlanArgs) -> str:
    """Build a study plan and prioritized tasks from recommendations and time budget."""
    try:
        runtime = get_runtime()
        learner_id = _learner_id(ctx)
        profile = runtime.learner_memory.get_profile(learner_id)

        recs: List[Dict[str, Any]] = []
        if args.recommendations_json.strip():
            recs = json.loads(args.recommendations_json).get("recommendations", [])
        if not recs:
            weak = (profile.get("knowledge_state_summary") or {}).get("weak_topics", [])
            recs = [{"title": f"Review {t}", "duration_minutes": 20, "topics": [t]} for t in weak[:3]]

        remaining = max(args.time_budget_minutes, 15)
        sessions: List[Dict[str, Any]] = []
        tasks: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)

        for idx, rec in enumerate(recs):
            duration = int(rec.get("duration_minutes", 25))
            if remaining <= 0:
                break
            duration = min(duration, remaining)
            remaining -= duration
            due = now + timedelta(days=idx)
            task_id = f"task_{learner_id}_{int(now.timestamp())}_{idx}"
            title = str(rec.get("title", f"Study session {idx + 1}"))
            tasks.append(
                {
                    "task_id": task_id,
                    "title": title,
                    "due_date": due.date().isoformat(),
                    "priority": "high" if idx == 0 else "medium",
                    "status": "pending",
                    "estimated_minutes": duration,
                }
            )
            sessions.append(
                {
                    "session": idx + 1,
                    "title": title,
                    "duration_minutes": duration,
                    "objective": f"Complete: {title}",
                }
            )

        study_plan = {"sessions": sessions, "total_minutes": args.time_budget_minutes - remaining}
        profile_tasks = profile.get("tasks", [])
        profile_tasks.extend(tasks)
        runtime.learner_memory.upsert_profile(
            learner_id, {"tasks": profile_tasks, "study_plan": study_plan}
        )

        return json.dumps({"study_plan": study_plan, "tasks": tasks}, ensure_ascii=False)
    except Exception as exc:
        logger.exception("create_study_plan_failed")
        return json.dumps({"error": str(exc), "study_plan": {}, "tasks": []})


@function_tool
async def list_learner_tasks(ctx: RunContextWrapper) -> str:
    """List current learner tasks from structured profile memory."""
    try:
        profile = _profile(ctx)
        return json.dumps({"tasks": profile.get("tasks", [])}, ensure_ascii=False)
    except Exception as exc:
        logger.exception("list_learner_tasks_failed")
        return json.dumps({"error": str(exc), "tasks": []})
