"""
High-level tutor request handlers used by FastAPI.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from dotenv import load_dotenv
from sqlalchemy import inspect, text

from agency.agency import get_agency
from agency.agents.RecommendationAgent import recommendation_agent
from agency.core.context import get_runtime
from agency.core.routing import detect_routing_hint
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


def _enrolled_match_terms(enrolled_courses: List[Dict[str, Any]]) -> set[str]:
    terms: set[str] = set()
    for course in enrolled_courses:
        code = str(course.get("code") or course.get("course_code") or "").strip().lower()
        title = str(course.get("title") or course.get("course_title") or "").strip().lower()
        if code:
            terms.add(code)
        if title:
            terms.add(title)
            for word in re.split(r"[^\w]+", title):
                if len(word) > 3:
                    terms.add(word)
    return terms


def _catalog_item_matches_enrolled(item: Dict[str, Any], terms: set[str]) -> bool:
    if not terms:
        return True
    blob = " ".join(
        [
            str(item.get("title", "")),
            str(item.get("topic", "")),
            " ".join(str(t) for t in item.get("topics", [])),
            " ".join(str(t) for t in item.get("tags", [])),
        ]
    ).lower()
    return any(term in blob for term in terms)


def _normalize_catalog_item_types(item: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from fastapi_app.services.content_type import normalize_content_item

        return normalize_content_item(item)
    except Exception:
        return item


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


def _extract_text_delta(event: Any) -> str:
    """Pull assistant text deltas from Agency Swarm / OpenAI stream events."""
    event_type = getattr(event, "type", None)
    if event_type == "raw_response_event":
        data = getattr(event, "data", None)
        if data is not None and getattr(data, "type", None) == "response.output_text.delta":
            return str(getattr(data, "delta", "") or "")
    if isinstance(event, dict):
        data = event.get("data")
        if isinstance(data, dict) and data.get("type") == "response.output_text.delta":
            return str(data.get("delta") or "")
    return ""


def _extract_final_output(result: Any) -> str:
    if hasattr(result, "final_output") and result.final_output:
        return str(result.final_output)
    if hasattr(result, "final_output_as") and callable(result.final_output_as):
        try:
            return str(result.final_output_as(str))
        except Exception:
            pass
    return str(result)


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _normalize_resource_title(title: str) -> str:
    return " ".join(str(title or "").lower().split())


def _unified_resource_list(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Merge recommendations and adaptive_path without duplicate titles."""
    seen: set[str] = set()
    unified: List[Dict[str, Any]] = []

    recs = data.get("recommendations")
    if isinstance(recs, list):
        for rec in recs:
            if not isinstance(rec, dict):
                continue
            title = str(rec.get("title") or rec.get("topic") or "").strip()
            key = _normalize_resource_title(title)
            if not key or key in seen:
                continue
            seen.add(key)
            unified.append(rec)

    adaptive = data.get("adaptive_path")
    if isinstance(adaptive, list):
        for step in adaptive:
            if not isinstance(step, dict):
                continue
            title = str(step.get("title") or step.get("topic") or "").strip()
            key = _normalize_resource_title(title)
            if not key or key in seen:
                continue
            seen.add(key)
            unified.append(step)

    return unified


def _looks_like_resource_list(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    numbered = sum(1 for line in lines if re.match(r"^\d+\.", line))
    return numbered >= 2


def _coerce_reasons(rec: Dict[str, Any]) -> List[str]:
    """Normalize reasons — LLM/tool output may use a string instead of a list."""
    raw = rec.get("reasons")
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if x and str(x).strip()]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    single = rec.get("reason")
    if isinstance(single, str) and single.strip():
        return [single.strip()]
    return []


def _clean_prose_lines(text: str) -> str:
    """Drop JSON syntax lines from a salvaged markdown section."""
    keep: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            keep.append("")
            continue
        if stripped.startswith(("{", "}", "[", "]", "```")):
            continue
        if re.match(r'^"[^"]+"\s*:', stripped):
            continue
        if '":' in stripped and stripped.count('"') >= 2:
            continue
        keep.append(line)
    return "\n".join(keep).strip()


def _salvage_prose_sections(text: str) -> str:
    """Extract readable markdown when agent output mixes invalid JSON with prose."""
    markers = (
        "### Study Plan",
        "### Study Session",
        "### Tasks",
        "**Study recommendations**",
        "**Your knowledge snapshot**",
    )
    sections: List[str] = []
    for marker in markers:
        idx = text.find(marker)
        if idx == -1:
            continue
        chunk = text[idx:]
        fence = chunk.find("```")
        if fence != -1:
            chunk = chunk[:fence]
        cleaned = _clean_prose_lines(chunk.strip())
        if cleaned and cleaned not in sections:
            sections.append(cleaned)
    return "\n\n".join(sections)


def _format_structured_payload(data: Any) -> str:
    if not isinstance(data, dict):
        return ""

    parts: List[str] = []

    summary = data.get("knowledge_state_summary")
    if isinstance(summary, dict):
        weak = summary.get("weak_topics") or []
        developing = summary.get("developing_topics") or []
        mastered = summary.get("mastered_topics") or []
        if weak or developing or mastered:
            parts.append("**Your knowledge snapshot**")
            if weak:
                parts.append(f"- **Focus areas:** {', '.join(str(t) for t in weak)}")
            if developing:
                parts.append(f"- **Developing:** {', '.join(str(t) for t in developing)}")
            if mastered:
                parts.append(f"- **Strong topics:** {', '.join(str(t) for t in mastered)}")
        trend = summary.get("trend")
        if trend and str(trend).lower() not in {"stable", "unknown"}:
            parts.append(f"- **Trend:** {trend}")

    notes = data.get("diagnostic_notes") or data.get("notes")
    if isinstance(notes, str) and notes.strip():
        parts.append(notes.strip())

    resources = _unified_resource_list(data)
    if resources:
        parts.append("**Study recommendations**")
        for i, rec in enumerate(resources[:6], 1):
            title = rec.get("title") or rec.get("topic") or "Resource"
            duration = rec.get("duration_minutes") or rec.get("estimated_minutes")
            modality = rec.get("modality") or rec.get("source_type") or ""
            reasons = _coerce_reasons(rec)
            meta = [str(modality).replace("_", " ").title()] if modality else []
            if duration:
                meta.append(f"{duration} min")
            line = f"{i}. **{title}**"
            if meta:
                line += f" ({', '.join(meta)})"
            parts.append(line)
            if reasons:
                parts.append(f"   - {' · '.join(reasons)}")

    study_plan = data.get("study_plan")
    if isinstance(study_plan, dict):
        sessions = study_plan.get("sessions") or []
        if sessions:
            parts.append("### Study Plan")
            total = study_plan.get("total_minutes")
            if total:
                parts.append(f"- **Total time:** {total} minutes")
            for sess in sessions:
                if not isinstance(sess, dict):
                    continue
                title = sess.get("title") or f"Session {sess.get('session', '')}"
                dur = sess.get("duration_minutes")
                objective = sess.get("objective") or ""
                line = f"- **{title}**"
                if dur:
                    line += f" ({dur} min)"
                parts.append(line)
                if objective:
                    parts.append(f"  - {objective}")

    tasks = data.get("tasks")
    if isinstance(tasks, list) and tasks:
        parts.append("### Tasks")
        for task in tasks:
            if not isinstance(task, dict):
                continue
            title = task.get("title") or "Task"
            due = task.get("due_date") or ""
            priority = task.get("priority") or ""
            est = task.get("estimated_minutes") or task.get("estimated_duration")
            meta = [m for m in [priority, f"due {due}" if due else None, f"{est} min" if est else None] if m]
            line = f"- **{title}**"
            if meta:
                line += f" ({', '.join(meta)})"
            parts.append(line)

    error = data.get("error")
    if error:
        parts.append(f"_{error}_")

    return "\n".join(parts)


def humanize_assistant_message(text: str) -> str:
    """Convert specialist JSON tool output into learner-friendly markdown."""
    if not text or not text.strip():
        return text

    stripped = text.strip()
    blocks = _JSON_FENCE_RE.findall(stripped)
    if not blocks:
        try:
            payload = json.loads(stripped)
            if isinstance(payload, dict):
                formatted = _format_structured_payload(payload)
                return formatted or text
        except json.JSONDecodeError:
            return text
        return text

    prose_parts: List[str] = []
    remainder = _JSON_FENCE_RE.sub("", stripped).strip()
    formatted_blocks: List[str] = []

    for block in blocks:
        try:
            payload = json.loads(block.strip())
            formatted = _format_structured_payload(payload)
            if formatted:
                formatted_blocks.append(formatted)
        except json.JSONDecodeError:
            continue

    if formatted_blocks:
        combined = "\n\n".join(formatted_blocks)
        if remainder and not _looks_like_resource_list(remainder):
            return f"{remainder}\n\n{combined}".strip()
        return combined

    salvaged = _salvage_prose_sections(stripped)
    if salvaged:
        return salvaged

    if remainder:
        prose_parts.append(remainder)

    return "\n\n".join(prose_parts).strip() or text


_SIMPLE_GREETINGS = {
    "hi",
    "hello",
    "hey",
    "what should i study",
    "help me",
    "good morning",
    "good afternoon",
    "good evening",
}
_SUBJECT_KEYWORDS = [
    "calculus",
    "algebra",
    "statistics",
    "algorithm",
    "physics",
    "chemistry",
    "explain",
    "how does",
    "what is",
    "help me understand",
    "solve",
    "prove",
    "derive",
    "integrate",
    "differentiate",
    "code",
    "program",
    "function",
    "theorem",
]


def _is_simple_message(message: str) -> bool:
    text = (message or "").strip().lower()
    if text in _SIMPLE_GREETINGS:
        return True
    words = text.split()
    if len(words) < 8 and not any(kw in text for kw in _SUBJECT_KEYWORDS):
        return True
    return False


def _handle_tutor_request_fast(
    *,
    learner_id: str,
    message: str,
    request_id: str,
    runtime: Any,
) -> str:
    from openai import OpenAI

    client = OpenAI()
    model = os.getenv("OPENAI_FAST_MODEL", "gpt-4o-mini")
    profile = runtime.learner_memory.get_profile(learner_id)
    name = profile.get("onboarding", {}).get("step1", {}).get("full_name") or "there"
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AITutor, a friendly academic assistant. "
                    "Keep replies concise and encouraging."
                ),
            },
            {"role": "user", "content": f"Learner name: {name}. Message: {message}"},
        ],
        max_tokens=300,
    )
    return (response.choices[0].message.content or "").strip() or "Hello! How can I help you study today?"


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

    if _is_simple_message(message) and os.getenv("OPENAI_API_KEY"):
        try:
            assistant_message = _handle_tutor_request_fast(
                learner_id=learner_id,
                message=message,
                request_id=request_id,
                runtime=runtime,
            )
            runtime.learner_memory.append_turn(learner_id, "assistant", assistant_message)
            return _build_response(request_id, learner_id, assistant_message, runtime)
        except Exception:
            logger.exception("fast_tutor_failed", extra={"request_id": request_id})

    try:
        result = agency.get_response_sync(
            prompt,
            context_override=user_context,
            additional_instructions=(
                f"{routing_hint}\n\nFollow the agency manifesto. "
                "Return a clear assistant_message in plain, friendly prose for the learner. "
                "Never output raw JSON or ``` code fences — translate specialist tool results into short paragraphs and numbered lists."
            ),
        )
        assistant_message = humanize_assistant_message(_extract_final_output(result))
    except Exception:
        logger.exception("agency_response_failed", extra={"request_id": request_id})
        assistant_message = (
            "I'm having trouble reaching the tutoring agents right now. "
            "Please verify your OpenAI API key and try again."
        )

    runtime.learner_memory.append_turn(learner_id, "assistant", assistant_message)
    return _build_response(request_id, learner_id, assistant_message, runtime)


async def handle_tutor_request_stream(
    *,
    learner_id: str,
    message: str,
    course_context: Optional[Dict[str, Any]] = None,
    events: Optional[List[Dict[str, Any]]] = None,
    time_budget_minutes: Optional[int] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """Stream tutoring response tokens via Agency Swarm get_response_stream."""
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
        "tutor_stream_start",
        extra={"request_id": request_id, "learner_id": learner_id, "routing_hint": routing_hint[:80]},
    )

    parts: List[str] = []
    assistant_message = ""

    try:
        stream = agency.get_response_stream(
            prompt,
            context_override=user_context,
            additional_instructions=(
                f"{routing_hint}\n\nFollow the agency manifesto. "
                "Return a clear assistant_message in plain, friendly prose for the learner. "
                "Never output raw JSON or ``` code fences — translate specialist tool results into short paragraphs and numbered lists."
            ),
        )
        # Buffer all agent tokens server-side — do NOT stream raw JSON/prose to the client.
        async for event in stream:
            delta = _extract_text_delta(event)
            if delta:
                parts.append(delta)

        try:
            result = await stream.wait_final_result()
            if result is not None:
                final_text = _extract_final_output(result).strip()
                if final_text and not parts:
                    parts.append(final_text)
        except Exception:
            logger.exception("tutor_stream_final_result_failed", extra={"request_id": request_id})

        assistant_message = humanize_assistant_message("".join(parts))
    except Exception:
        logger.exception("tutor_stream_failed", extra={"request_id": request_id})
        assistant_message = (
            "I'm having trouble reaching the tutoring agents right now. "
            "Please verify your OpenAI API key and try again."
        )

    if not assistant_message.strip():
        assistant_message = (
            "I processed your request but could not generate a visible reply. Please try again."
        )

    runtime.learner_memory.append_turn(learner_id, "assistant", assistant_message)
    payload = _build_response(request_id, learner_id, assistant_message, runtime)
    yield {"type": "done", **payload}


def _dedupe_recommendations(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep one entry per content item, preferring the highest score."""
    seen: Dict[str, Dict[str, Any]] = {}
    for item in items:
        item_id = str(item.get("item_id") or item.get("id") or item.get("content_item_id") or "")
        if not item_id:
            continue
        score = float(item.get("match_score", item.get("score", 0)) or 0)
        existing = seen.get(item_id)
        if existing is None:
            seen[item_id] = item
            continue
        existing_score = float(existing.get("match_score", existing.get("score", 0)) or 0)
        if score > existing_score:
            seen[item_id] = item
    return list(seen.values())


def _dedupe_catalog(catalog: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate catalog entries before scoring."""
    deduped = _dedupe_recommendations(catalog)
    return deduped if deduped else catalog


def handle_recommend_request(
    *,
    learner_id: str,
    message: str = "what should I study next",
    course_context: Optional[Dict[str, Any]] = None,
    events: Optional[List[Dict[str, Any]]] = None,
    limit: int = 6,
    use_agent: bool = False,
    enrolled_courses: Optional[List[Dict[str, Any]]] = None,
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
    weak_quiz_topics = profile.get("weak_quiz_topics") or []
    if weak_quiz_topics:
        weak_topics = list(dict.fromkeys(list(weak_topics) + list(weak_quiz_topics)))
    if enrolled_courses:
        for course in enrolled_courses:
            title = str(course.get("title") or course.get("course_title") or "")
            code = str(course.get("code") or course.get("course_code") or "")
            if title:
                weak_topics = list(weak_topics) + [title]
            if code:
                weak_topics = list(weak_topics) + [code]
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

    from fastapi_app.services.content_ingestion_service import NO_CONTENT_MESSAGE
    from fastapi_app.services.content_relevance import filter_content_by_enrolled_courses

    catalog = [_normalize_catalog_item_types(item) for item in runtime.catalog]
    catalog = _dedupe_catalog(catalog)
    if enrolled_courses:
        relevant_catalog = filter_content_by_enrolled_courses(catalog, enrolled_courses)
        if not relevant_catalog:
            return {
                "request_id": request_id,
                "learner_id": learner_id,
                "source": "hybrid_recommender",
                "recommendations": [],
                "adaptive_path": [],
                "status": "no_content_for_courses",
                "message": NO_CONTENT_MESSAGE,
                "timestamp": utc_now().isoformat(),
            }
        catalog = relevant_catalog

    catalog = [
        item
        for item in catalog
        if str(item.get("source_origin", "")).strip().lower() != "lecturer_upload"
    ]
    if not catalog:
        return {
            "request_id": request_id,
            "learner_id": learner_id,
            "source": "hybrid_recommender",
            "recommendations": [],
            "adaptive_path": [],
            "status": "no_content_for_courses",
            "message": NO_CONTENT_MESSAGE,
            "timestamp": utc_now().isoformat(),
        }

    ranked, adaptive_path = hybrid_recommend(
        catalog=catalog,
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
            "source_type": _normalize_catalog_item_types(r.payload).get("source_type"),
            "provider": r.payload.get("provider"),
            "source_url": r.payload.get("source_url") or r.payload.get("url") or r.payload.get("external_url"),
            "score": round(r.score, 3),
            "reasons": r.reasons,
            "reason": " · ".join(r.reasons) if r.reasons else "Recommended for your learning path",
        }
        for r in ranked
    ]
    recommendations = _dedupe_recommendations(recommendations)
    recommendations.sort(key=lambda x: float(x.get("score", 0)), reverse=True)
    recommendations = recommendations[:limit]
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
            from scripts.ingest_ebooks import _filter_ebook_candidates

            ebook_candidates = fetch_ebook_learning_items(
                selected_topics,
                max_per_topic=max_per_topic,
                candidates_per_topic=max(max_per_topic * 8, 15),
            )
            fetched_items.extend(
                _filter_ebook_candidates(ebook_candidates, max_per_topic=max_per_topic)
            )

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
