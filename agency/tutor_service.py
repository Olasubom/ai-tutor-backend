"""
High-level tutor request handlers used by FastAPI.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from sqlalchemy import inspect, text

from agency.agency import get_agency
from agency.agents.RecommendationAgent import recommendation_agent
from agency.core.context import get_runtime
from agency.core.routing import detect_routing_hint
from agency.core.services.bkt import apply_events
from agency.core.services.recommender import hybrid_recommend
from agency.core.tools.database import Database
from agency.core.tools.source_ingestion import fetch_ebook_learning_items, fetch_youtube_learning_items
from agency.core.utils import configure_logging, new_request_id, utc_now

logger = logging.getLogger(__name__)

_ENV_PATH = Path(__file__).resolve().parent / ".env"
_MODALITY_ALIASES = {
    "video": {"video", "videos"},
    "text": {"text", "reading", "read", "notes"},
    "interactive": {"interactive", "hands-on", "hands on", "practice"},
    "game": {"game", "games", "gamified"},
    "read_aloud": {"read aloud", "audio", "narration", "narrated"},
}


def _ensure_env() -> None:
    if _ENV_PATH.exists():
        load_dotenv(_ENV_PATH, override=True)


def _format_user_message(
    *,
    message: str,
    course_context: Optional[Dict[str, Any]] = None,
    events: Optional[List[Dict[str, Any]]] = None,
    time_budget_minutes: Optional[int] = None,
) -> str:
    parts = [f"Learner message: {message}"]
    if course_context:
        parts.append(f"Course context: {json.dumps(course_context, ensure_ascii=False)}")
    if events:
        parts.append(f"Performance events: {json.dumps(events, ensure_ascii=False)}")
    if time_budget_minutes is not None:
        parts.append(f"Time budget (minutes): {time_budget_minutes}")
    return "\n".join(parts)


def _extract_final_output(result: Any) -> str:
    if hasattr(result, "final_output") and result.final_output:
        return str(result.final_output)
    if hasattr(result, "final_output_as") and callable(result.final_output_as):
        try:
            return str(result.final_output_as(str))
        except Exception:
            pass
    return str(result)


def _extract_modalities_from_message(message: str) -> List[str]:
    """Infer explicit modality preferences from learner message text."""
    text = (message or "").lower()
    found: List[str] = []
    for modality, aliases in _MODALITY_ALIASES.items():
        if any(alias in text for alias in aliases):
            found.append(modality)
    return found


def handle_tutor_request(
    *,
    learner_id: str,
    message: str,
    course_context: Optional[Dict[str, Any]] = None,
    events: Optional[List[Dict[str, Any]]] = None,
    time_budget_minutes: Optional[int] = None,
) -> Dict[str, Any]:
    """Process a full tutoring chat request through the Coordinator agent."""
    _ensure_env()
    configure_logging()
    request_id = new_request_id()
    runtime = get_runtime()

    stated_modalities = _extract_modalities_from_message(message)
    if stated_modalities:
        runtime.learner_memory.update_preferred_modalities(
            learner_id=learner_id,
            modalities=stated_modalities,
            confidence=0.9,
        )

    if events:
        runtime.learner_memory.update_learner_profile(learner_id, events)

    runtime.learner_memory.append_turn(learner_id, "user", message)

    user_context: Dict[str, Any] = {
        "learner_id": learner_id,
        "request_id": request_id,
        "course_context": course_context or {},
        "events": events or [],
        "time_budget_minutes": time_budget_minutes,
    }

    routing_hint = detect_routing_hint(message, has_events=bool(events))
    agency = get_agency()
    prompt = _format_user_message(
        message=message,
        course_context=course_context,
        events=events,
        time_budget_minutes=time_budget_minutes,
    )

    logger.info(
        "tutor_request_start",
        extra={"request_id": request_id, "learner_id": learner_id, "routing_hint": routing_hint[:80]},
    )

    try:
        result = agency.get_response_sync(
            prompt,
            context_override=user_context,
            additional_instructions=(
                f"{routing_hint}\n\nFollow the agency manifesto. "
                "Return a clear assistant_message and structured artifacts when available."
            ),
        )
        assistant_message = _extract_final_output(result)
    except Exception:
        logger.exception("agency_response_failed", extra={"request_id": request_id})
        assistant_message = (
            "I'm having trouble reaching the tutoring agents right now. "
            "Please verify your OpenAI API key and try again."
        )

    runtime.learner_memory.append_turn(learner_id, "assistant", assistant_message)
    return _build_response(request_id, learner_id, assistant_message, runtime)


def handle_recommend_request(
    *,
    learner_id: str,
    message: str = "what should I study next",
    course_context: Optional[Dict[str, Any]] = None,
    events: Optional[List[Dict[str, Any]]] = None,
    limit: int = 6,
    use_agent: bool = False,
) -> Dict[str, Any]:
    """
    Direct recommendations without full Coordinator chat.

    By default uses deterministic hybrid_recommend (fast, no LLM).
    Set use_agent=True to delegate to RecommendationAgent via Agency Swarm.
    """
    _ensure_env()
    configure_logging()
    request_id = new_request_id()
    runtime = get_runtime()
    stated_modalities = _extract_modalities_from_message(message)
    if stated_modalities:
        runtime.learner_memory.update_preferred_modalities(
            learner_id=learner_id,
            modalities=stated_modalities,
            confidence=0.9,
        )

    if events:
        runtime.learner_memory.update_learner_profile(learner_id, events)
        profile = runtime.learner_memory.get_profile(learner_id)
        topic_mastery = profile.get("topic_mastery", {})
        topic_mastery, summary = apply_events(topic_mastery, events)
        runtime.learner_memory.upsert_profile(
            learner_id,
            {"topic_mastery": topic_mastery, "knowledge_state_summary": summary},
        )

    if use_agent and os.getenv("OPENAI_API_KEY"):
        try:
            agency = get_agency()
            result = agency.get_response_sync(
                _format_user_message(message=message, course_context=course_context, events=events),
                recipient_agent=recommendation_agent,
                context_override={"learner_id": learner_id, "request_id": request_id},
                additional_instructions="Return JSON with recommendations and adaptive_path only.",
            )
            text = _extract_final_output(result)
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = {"raw": text}
            return {
                "request_id": request_id,
                "learner_id": learner_id,
                "source": "RecommendationAgent",
                "recommendations": payload.get("recommendations", payload),
                "adaptive_path": payload.get("adaptive_path", []),
                "timestamp": utc_now().isoformat(),
            }
        except Exception:
            logger.exception("recommend_agent_failed", extra={"request_id": request_id})

    # Deterministic path (default)
    mem = runtime.learner_memory.get_relevant_memory(learner_id, message, k=8)
    profile = runtime.learner_memory.get_profile(learner_id)
    highlights = mem.get("profile_highlights", {})
    weak_topics = highlights.get("weak_topics") or (
        (profile.get("knowledge_state_summary") or {}).get("weak_topics", [])
    )
    preferences = profile.get("preferences", {})
    preferred_modalities = (
        highlights.get("preferred_modalities", [])
        if isinstance(highlights, dict)
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
        limit=limit,
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
            "reason": " · ".join(r.reasons) if r.reasons else "Recommended for your learning path",
        }
        for r in ranked
    ]
    payload = {"recommendations": recommendations, "adaptive_path": adaptive_path}
    runtime.learner_memory.upsert_profile(learner_id, {"last_recommendations": payload})

    logger.info("recommend_request_ok", extra={"request_id": request_id, "learner_id": learner_id})

    return {
        "request_id": request_id,
        "learner_id": learner_id,
        "source": "hybrid_recommender",
        "memory_used": mem,
        "recommendations": recommendations,
        "adaptive_path": adaptive_path,
        "timestamp": utc_now().isoformat(),
    }


def _build_response(
    request_id: str,
    learner_id: str,
    assistant_message: str,
    runtime: Any,
) -> Dict[str, Any]:
    profile = runtime.learner_memory.get_profile(learner_id)
    artifacts: Dict[str, Any] = {
        "recommendations": profile.get("last_recommendations"),
        "study_plan": profile.get("study_plan"),
        "tasks": profile.get("tasks"),
        "knowledge_state_summary": profile.get("knowledge_state_summary"),
    }
    return {
        "request_id": request_id,
        "learner_id": learner_id,
        "assistant_message": assistant_message,
        "artifacts": {k: v for k, v in artifacts.items() if v is not None},
        "timestamp": utc_now().isoformat(),
    }


def get_learner_profile_snapshot(learner_id: str) -> Dict[str, Any]:
    """
    Return a debug snapshot of personalization inputs for a learner.

    This is useful for validating recommendation behavior per learner.
    """
    _ensure_env()
    configure_logging()
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    memory = runtime.learner_memory.get_relevant_memory(
        learner_id=learner_id,
        query="personalization snapshot",
        k=5,
    )
    return {
        "learner_id": learner_id,
        "profile": profile,
        "memory": memory,
        "timestamp": utc_now().isoformat(),
    }


def get_db_health_snapshot() -> Dict[str, Any]:
    """Return DB connectivity and basic row counts for core persistence tables."""
    _ensure_env()
    configure_logging()
    db = Database()
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    counts: Dict[str, int] = {}
    wanted = ["learners", "interactions", "topic_mastery", "tasks", "content_items"]
    with db.engine.connect() as conn:
        for table in wanted:
            if table not in tables:
                counts[table] = -1
                continue
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            counts[table] = int(result.scalar_one())

    return {
        "database_url": str(db.engine.url).replace(str(db.engine.url.password or ""), "***")
        if db.engine.url.password
        else str(db.engine.url),
        "tables": tables,
        "counts": counts,
        "timestamp": utc_now().isoformat(),
    }


def reset_learner_state(learner_id: str) -> Dict[str, Any]:
    """
    Dev utility to clear one learner's stored state.

    Protected by `ALLOW_DEV_ENDPOINTS=true` in environment.
    """
    _ensure_env()
    if str(os.getenv("ALLOW_DEV_ENDPOINTS", "false")).lower() != "true":
        raise PermissionError("Dev endpoints are disabled. Set ALLOW_DEV_ENDPOINTS=true to use this route.")
    runtime = get_runtime()
    payload = runtime.learner_memory.reset_learner(learner_id=learner_id)
    payload["timestamp"] = utc_now().isoformat()
    return payload


def ingest_source_items(source: str, topics: Optional[List[str]] = None, max_per_topic: int = 5) -> Dict[str, Any]:
    """
    Dev utility to ingest external learning resources into DB-backed content_items.

    Protected by `ALLOW_DEV_ENDPOINTS=true` in environment.
    """
    _ensure_env()
    if str(os.getenv("ALLOW_DEV_ENDPOINTS", "false")).lower() != "true":
        raise PermissionError("Dev endpoints are disabled. Set ALLOW_DEV_ENDPOINTS=true to use this route.")

    runtime = get_runtime()
    if runtime.repository is None:
        raise RuntimeError("Repository unavailable. Configure DATABASE_URL for DB-backed ingestion.")

    selected_topics = topics or sorted(
        {
            str(item.get("topic"))
            for item in runtime.catalog
            if isinstance(item, dict) and item.get("topic")
        }
    )
    if not selected_topics:
        selected_topics = ["Algebra", "Geometry", "Algorithms", "Python"]

    normalized_source = source.strip().lower()
    if normalized_source not in {"youtube", "ebooks", "ebook", "all"}:
        raise ValueError("Invalid source. Use one of: youtube, ebooks, all.")

    requested_count = len(selected_topics) * max(1, int(max_per_topic))
    fetched_items: List[Dict[str, Any]] = []
    written = 0
    deduped_count = 0
    run_status = "success"
    run_error = None
    try:
        if normalized_source in {"youtube", "all"}:
            fetched_items.extend(fetch_youtube_learning_items(selected_topics, max_per_topic=max_per_topic))
        if normalized_source in {"ebooks", "ebook", "all"}:
            fetched_items.extend(fetch_ebook_learning_items(selected_topics, max_per_topic=max_per_topic))

        deduped: List[Dict[str, Any]] = []
        seen_keys = set()
        for item in fetched_items:
            if not isinstance(item, dict):
                continue
            key = (
                str(item.get("source_url") or "").strip().lower(),
                str(item.get("title") or "").strip().lower(),
                str(item.get("provider") or "").strip().lower(),
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(item)

        deduped_count = len(deduped)
        written = runtime.repository.upsert_content_items(deduped)
    except Exception as exc:
        run_status = "failed"
        run_error = str(exc)
        logger.exception("ingest_source_items_failed", extra={"source": normalized_source})
        raise
    finally:
        if runtime.repository is not None:
            try:
                runtime.repository.create_ingestion_run(
                    source=normalized_source,
                    topics=selected_topics,
                    requested_count=requested_count,
                    fetched_count=len(fetched_items),
                    deduped_count=deduped_count,
                    written_count=written,
                    status=run_status,
                    error=run_error,
                )
            except Exception:
                logger.exception("ingestion_run_write_failed", extra={"source": normalized_source})

    runtime.catalog = runtime.repository.list_content_items(limit=5000) or runtime.catalog

    return {
        "source": normalized_source,
        "topics": selected_topics,
        "fetched": len(fetched_items),
        "deduped": deduped_count,
        "written": written,
        "catalog_size": len(runtime.catalog),
        "timestamp": utc_now().isoformat(),
    }


def list_content_items_snapshot(
    *,
    topic: Optional[str] = None,
    modality: Optional[str] = None,
    source_type: Optional[str] = None,
    source_origin: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """Return filtered content items from DB-backed catalog for debugging."""
    _ensure_env()
    if str(os.getenv("ALLOW_DEV_ENDPOINTS", "false")).lower() != "true":
        raise PermissionError("Dev endpoints are disabled. Set ALLOW_DEV_ENDPOINTS=true to use this route.")

    runtime = get_runtime()
    if runtime.repository is None:
        raise RuntimeError("Repository unavailable. Configure DATABASE_URL for DB-backed catalog browsing.")

    items = runtime.repository.list_content_items(
        limit=limit,
        topic=topic,
        modality=modality,
        source_type=source_type,
    )
    if source_origin:
        normalized_origin = source_origin.strip().lower()
        items = [
            item
            for item in items
            if str(item.get("source_origin", "")).strip().lower() == normalized_origin
        ]
        items = items[:limit]
    return {
        "filters": {
            "topic": topic,
            "modality": modality,
            "source_type": source_type,
            "source_origin": source_origin,
            "limit": limit,
        },
        "count": len(items),
        "items": items,
        "timestamp": utc_now().isoformat(),
    }


def backfill_content_source_origin() -> Dict[str, Any]:
    """Dev utility to backfill source_origin on legacy content_items rows."""
    _ensure_env()
    if str(os.getenv("ALLOW_DEV_ENDPOINTS", "false")).lower() != "true":
        raise PermissionError("Dev endpoints are disabled. Set ALLOW_DEV_ENDPOINTS=true to use this route.")

    runtime = get_runtime()
    if runtime.repository is None:
        raise RuntimeError("Repository unavailable. Configure DATABASE_URL for content backfill.")

    counts = runtime.repository.backfill_source_origin()
    runtime.catalog = runtime.repository.list_content_items(limit=5000) or runtime.catalog
    return {
        "counts": counts,
        "catalog_size": len(runtime.catalog),
        "timestamp": utc_now().isoformat(),
    }


def list_ingestion_history_snapshot(limit: int = 20) -> Dict[str, Any]:
    """Return recent ingestion runs for operational visibility."""
    _ensure_env()
    if str(os.getenv("ALLOW_DEV_ENDPOINTS", "false")).lower() != "true":
        raise PermissionError("Dev endpoints are disabled. Set ALLOW_DEV_ENDPOINTS=true to use this route.")

    runtime = get_runtime()
    if runtime.repository is None:
        raise RuntimeError("Repository unavailable. Configure DATABASE_URL for ingestion history.")

    runs = runtime.repository.list_ingestion_runs(limit=max(1, min(int(limit), 200)))
    return {
        "count": len(runs),
        "runs": runs,
        "timestamp": utc_now().isoformat(),
    }
