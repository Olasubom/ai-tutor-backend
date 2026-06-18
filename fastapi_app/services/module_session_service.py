"""Module session state machine: explanation → tasks → quiz → completed."""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.core.context import get_runtime
from agency.core.tools.models import ContentItem, ModuleSession, TopicMastery
from fastapi_app.services.module_embedding_service import get_ordered_chunks, retrieve_relevant_chunks
from fastapi_app.services.module_progress_service import upsert_module_progress
from fastapi_app.services import quiz_service

logger = logging.getLogger(__name__)

_ADVANCE_KEYWORDS = frozenset({
    "next",
    "continue",
    "got it",
    "i understand",
    "understood",
    "move on",
    "ready",
    "done",
    "proceed",
    "go ahead",
    "next part",
    "move forward",
    "let's continue",
    "next section",
    "let me continue",
    "i'm ready",
    "let's go",
    "keep going",
})


def _classify_advance(message: Optional[str]) -> bool:
    if not message:
        return False
    lower = message.lower().strip()
    return any(kw in lower for kw in _ADVANCE_KEYWORDS)


def classify_ready_to_advance(message: Optional[str]) -> bool:
    """Backward-compatible alias — use _classify_advance (yes/ok do not advance)."""
    return _classify_advance(message)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _openai_client() -> Optional[OpenAI]:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or "your_key" in key.lower():
        return None
    return OpenAI(api_key=key)


def _call_llm(user_prompt: str, system_prompt: str = "") -> str:
    """Mirror LLM call pattern from agency/tutor_service.py (_handle_tutor_request_fast)."""
    client = _openai_client()
    if not client:
        return ""
    model = os.getenv("OPENAI_MODEL", os.getenv("OPENAI_FAST_MODEL", "gpt-4o"))
    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=800,
            temperature=0.7,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        logger.exception("module_session_llm_failed")
        return ""


_FORMAT_TO_LABEL = {
    "video": "Video Lectures",
    "text": "Written Material",
    "interactive": "Interactive Quizzes",
    "mixed": "Mixed Approach",
}


def _get_learner_preferences(learner_id: str) -> tuple[str, str]:
    """Read content format + goal from learner memory (Settings → onboarding step4)."""
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    prefs = profile.get("preferences") or {}
    step4 = (profile.get("onboarding") or {}).get("step4") or prefs
    formats = step4.get("content_formats") or prefs.get("content_formats") or ["mixed"]
    if not isinstance(formats, list) or not formats:
        formats = ["mixed"]
    if len(formats) > 1:
        preferred_type = "Mixed Approach"
    else:
        preferred_type = _FORMAT_TO_LABEL.get(str(formats[0]).lower(), "Mixed Approach")
    objective = str(step4.get("primary_objective") or prefs.get("primary_objective") or "Academic Excellence")
    return preferred_type, objective


def get_topic_mastery(learner_id: str, topic: str, db: Session) -> float:
    return _get_topic_mastery(learner_id, topic, db)


def _get_topic_mastery(learner_id: str, topic: str, db: Session) -> float:
    """BKT mastery from TopicMastery table, then learner memory fallback."""
    try:
        record = db.scalars(
            select(TopicMastery)
            .where(
                TopicMastery.learner_id == learner_id,
                TopicMastery.topic.ilike(f"%{topic}%"),
            )
            .order_by(TopicMastery.updated_at.desc())
        ).first()
        if record is not None:
            return float(record.p_l or 0)
    except Exception:
        logger.exception("get_topic_mastery_db_failed", extra={"learner_id": learner_id, "topic": topic})

    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    state = profile.get("topic_mastery", {}).get(topic, {})
    if state:
        return float(state.get("p_l", 0.3))

    topic_lower = topic.lower()
    for key, val in profile.get("topic_mastery", {}).items():
        if topic_lower in str(key).lower() or str(key).lower() in topic_lower:
            return float(val.get("p_l", 0.3))
    return 0.0


def generate_onboarding_message(content_item: ContentItem, mastery: float) -> str:
    """Single familiarity question — does not re-ask Settings content preferences."""
    topic = content_item.title
    if mastery < 0.15:
        return (
            f"Welcome! Before we get into **{topic}** — "
            f"is this completely new to you, or have you seen it before "
            f"in class or from reading?"
        )
    if mastery < 0.35:
        return (
            f"You've had some exposure to **{topic}** already. "
            f"What feels shakiest right now — the core definitions, "
            f"how they apply in real legal cases, or both?"
        )
    if mastery < 0.6:
        return (
            f"You have a reasonable foundation on **{topic}**. "
            f"Should I focus on the parts students usually find tricky, "
            f"or do a complete walkthrough from the beginning?"
        )
    return (
        f"Your mastery on **{topic}** is already solid. "
        f"Full review to reinforce everything, or straight to the "
        f"advanced and exam-critical points?"
    )


def generate_chunk_explanation(
    *,
    chunk_text: str,
    content_item: ContentItem,
    learner_id: str,
    session_data: dict,
    db: Session,
    student_message: Optional[str] = None,
) -> str:
    """Image-1-style structured explanation calibrated by BKT + Settings preferences."""
    preferred_type, primary_goal = _get_learner_preferences(learner_id)
    mastery = _get_topic_mastery(learner_id, content_item.title, db)
    onboarding_response = session_data.get("onboarding_response", "")
    chunks_delivered = int(session_data.get("chunks_delivered_count", 0))

    if mastery < 0.2:
        depth = (
            "Complete beginner — very low mastery score. "
            "Define EVERY term. Short, simple sentences. Zero assumptions."
        )
    elif mastery < 0.5:
        depth = (
            "Some familiarity — skip obvious definitions. "
            "Focus on nuance, common misconceptions, connecting concepts."
        )
    else:
        depth = (
            "Advanced — go deeper. Edge cases, exceptions, "
            "advanced applications. Challenge assumptions."
        )

    style_map = {
        "Video Lectures": (
            "Explain like a documentary narrator. Vivid, scene-by-scene scenarios. "
            "Make the student PICTURE the concept. Nigerian examples essential: "
            "courts in Lagos, markets in Onitsha, banks on Victoria Island, "
            "MTN/Glo/Airtel towers, Dangote factories, OPay wallets."
        ),
        "Written Material": (
            "Precise academic language. Structure: formal definition first, "
            "then clause-by-clause with one example per clause. "
            "Reference Nigerian statutes, case law, or commercial practice "
            "(Nigerian Contract Act, CAMA, court decisions, FIRS, CBN policies)."
        ),
        "Interactive Quizzes": (
            "After explaining each key point (1-2 sentences), immediately ask "
            "a brief comprehension check: 'Quick check — what does X mean?' "
            "or 'Can you give me an example of Y?'. Encourage, then continue."
        ),
        "Mixed Approach": (
            "Alternate between precise academic definition and vivid real-world "
            "Nigerian example. OPay, GTBank, Dangote, Jumia, NNPC, Alaba market. "
            "Vary sentence structure. Keep it engaging."
        ),
    }
    style = style_map.get(preferred_type, style_map["Mixed Approach"])

    question_addon = ""
    if (
        student_message
        and chunks_delivered > 0
        and len(student_message.strip()) > 8
        and not _classify_advance(student_message)
    ):
        question_addon = (
            f'\n\nThe student just said: "{student_message}". '
            "Address this directly. If it's a question, answer using the content. "
            "If confusion, simplify that specific concept."
        )

    payload = content_item.payload_json or {}
    description = str(payload.get("description") or payload.get("summary") or "")
    context = chunk_text.strip() if chunk_text.strip() else (
        f"Topic: {content_item.title}\nDescription: {description or 'No description'}"
    )

    goal_addon = ""
    if primary_goal == "Academic Excellence":
        goal_addon = (
            "\nThis student is focused on exam performance. "
            "When there is a 'must memorize' moment, call it out explicitly."
        )

    prompt = f"""You are an AI tutor at Fountain University, Osogbo, Nigeria.
Teaching a Law student one-on-one.

TOPIC: {content_item.title}

CONTENT:
{context}

STUDENT PRIOR LEVEL (their words from onboarding): "{onboarding_response or 'not specified'}"
DEPTH: {depth}
STYLE: {style}{goal_addon}{question_addon}

═══ REQUIRED FORMAT — follow this EXACTLY ═══

**{content_item.title}**

📖 **The Definition**
*[Quote the key definition or opening sentence from the content in italics]*

Breaking it down:

*"[First key phrase]"*
→ [Explain in 1-2 plain sentences]
→ **Nigerian example:** [Specific scenario — real companies, cities, cases]

*"[Second key phrase]"*
→ [Explain in 1-2 plain sentences]
→ **Nigerian example:** [Another specific Nigerian scenario]

[Continue for each important clause]

[If one sentence is critically important for the exam:]
> 🔑 **Memorize this:** [The sentence]

---
Does this make sense? Ask any questions or say **'next'** to continue.

═══ RULES ═══
- Under 300 words total
- NEVER generic examples (no "John and Mary", no "Company A")
- ALWAYS Nigerian context: MTN, Airtel, OPay, GTBank, Access Bank, Zenith,
  Dangote, NNPC, Jumia, Konga, Alaba market, Lagos courts, CBN, FIRS
- Each phrase gets its own Nigerian example
- Explain clause-by-clause, not summary
- Markdown is rendered — use it"""

    text = _call_llm(
        prompt,
        system_prompt="You are a warm, precise academic tutor for Nigerian law students.",
    )
    if text:
        return text

    return (
        f"### {content_item.title}\n\n"
        f"{chunk_text[:1200]}{'…' if len(chunk_text) > 1200 else ''}\n\n"
        "Let me know when you're ready for the next part."
    )


def generate_module_explanation(
    content_item: ContentItem,
    session: ModuleSession,
    mastery: float,
    chunk_index: int,
    db: Session,
) -> str:
    del mastery
    chunks = get_ordered_chunks(content_item.item_id)
    if not chunks:
        rag = retrieve_relevant_chunks(content_item.item_id, content_item.title or "", top_k=5)
        if rag:
            chunks = rag
    if not chunks:
        status = content_item.embedding_status or "pending"
        if status in {"pending", "failed"}:
            return (
                f"Welcome to **{content_item.title}**! "
                "I'm still processing the PDF for this module. "
                "I'll explain the material using what I have — ask questions anytime, "
                "or say **next** when you're ready to move on."
            )
        return (
            f"Welcome to **{content_item.title}**! "
            "Let's work through this module together. Say **next** when you're ready to continue."
        )
    idx = min(chunk_index, len(chunks) - 1)
    return generate_chunk_explanation(
        chunk_text=chunks[idx],
        content_item=content_item,
        learner_id=session.learner_id,
        session_data=_parse_session_data(session),
        db=db,
    )


def _content_item_origin(item: ContentItem) -> str:
    return str((item.payload_json or {}).get("source_origin", "")).strip().lower()


def _content_item_description(item: ContentItem) -> str:
    payload = item.payload_json or {}
    return str(payload.get("description") or payload.get("summary") or "")


def _item_source_type(item: ContentItem) -> str:
    from fastapi_app.services.content_type import normalize_source_type

    return normalize_source_type(item.source_type, item.title)


def _topic_relevance_score(item: ContentItem, topic: str) -> int:
    from fastapi_app.services.content_relevance import _title_keywords

    topic_words = _title_keywords(topic)
    if not topic_words:
        return 0
    item_text = f"{item.title} {item.topic or ''} {_content_item_description(item)}".lower()
    item_words = set(re.findall(r"\w+", item_text))
    return len(topic_words & item_words)


def _item_to_recommendation(item: ContentItem) -> Dict[str, Any]:
    payload = item.payload_json or {}
    return {
        "id": item.item_id,
        "item_id": item.item_id,
        "title": item.title,
        "description": _content_item_description(item),
        "source_type": _item_source_type(item),
        "source_url": item.source_url or payload.get("source_url") or payload.get("url"),
        "modality": item.modality,
    }


def get_recommendations_for_topic(
    *,
    learner_id: str,
    topic: str,
    limit: int,
    db: Session,
    exclude_content_item_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    preferred_type, _ = _get_learner_preferences(learner_id)
    type_map = {
        "Video Lectures": ["video"],
        "Written Material": ["article", "ebook"],
        "Interactive Quizzes": ["quiz", "article", "interactive"],
        "Mixed Approach": ["video", "article", "ebook", "quiz", "interactive"],
    }
    allowed_types = type_map.get(preferred_type, type_map["Mixed Approach"])

    items = db.scalars(select(ContentItem).where(ContentItem.status == "approved")).all()
    external: List[ContentItem] = []
    for item in items:
        if exclude_content_item_id and item.item_id == exclude_content_item_id:
            continue
        if _content_item_origin(item) == "lecturer_upload":
            continue
        if _item_source_type(item) not in allowed_types:
            continue
        external.append(item)

    scored = sorted(external, key=lambda i: _topic_relevance_score(i, topic), reverse=True)
    relevant = [i for i in scored if _topic_relevance_score(i, topic) > 0]
    if not relevant:
        relevant = scored

    recs = [_item_to_recommendation(item) for item in relevant[:limit]]
    if recs:
        return recs

    q = urllib.parse.quote(f"{topic} explained Nigeria law")
    return [
        {
            "id": "fallback_yt",
            "item_id": "fallback_yt",
            "title": f"Search YouTube: '{topic} explained'",
            "description": (
                f"Find video explanations of {topic} "
                f"from Nigerian and international educators."
            ),
            "source_type": "video",
            "source_url": f"https://www.youtube.com/results?search_query={q}",
            "is_fallback": True,
        }
    ]


def generate_quiz_for_topic(
    *,
    learner_id: str,
    topic: str,
    num_questions: int = 5,
) -> dict:
    return quiz_service.generate_quiz(learner_id, topic, num_questions)


def _parse_session_data(session: ModuleSession) -> dict:
    try:
        return json.loads(session.session_data or "{}")
    except json.JSONDecodeError:
        return {}


def _save_session_data(session: ModuleSession, data: dict, db: Session) -> None:
    session.session_data = json.dumps(data)
    session.updated_at = _now()
    db.commit()


def handle_onboarding_stage(
    session: ModuleSession,
    content_item: ContentItem,
    message: Optional[str],
    db: Session,
) -> dict:
    session_data = _parse_session_data(session)
    if message and message.strip():
        session_data["onboarding_response"] = message.strip()
        session.stage = "explanation"
        session.updated_at = _now()
        _save_session_data(session, session_data, db)
        return handle_explanation_stage(session, content_item, content_item.title, db)

    mastery = get_topic_mastery(session.learner_id, content_item.title, db)
    return {
        "stage": "onboarding",
        "message": generate_onboarding_message(content_item, mastery),
        "pdf_url": content_item.source_url,
    }


def handle_explanation_stage(
    session: ModuleSession,
    content_item: ContentItem,
    message: Optional[str],
    db: Session,
) -> dict:
    session_data = _parse_session_data(session)
    chunks_delivered = int(session_data.get("chunks_delivered_count", 0))
    next_index = session.explanation_progress

    is_real_question = (
        message
        and len(message.strip()) > 10
        and chunks_delivered > 0
        and not _classify_advance(message)
    )
    rag_query = message if is_real_question else (content_item.title or "")

    chunks = retrieve_relevant_chunks(content_item.item_id, query=rag_query, top_k=4)
    if not chunks:
        all_ordered = get_ordered_chunks(content_item.item_id)
        if all_ordered and next_index < len(all_ordered):
            chunks = [all_ordered[next_index]]
        else:
            chunks = []

    should_advance = (
        chunks_delivered > 0
        and (
            chunks_delivered >= 6
            or not chunks
            or _classify_advance(message)
        )
    )

    if should_advance:
        session.stage = "tasks"
        session.updated_at = _now()
        db.commit()
        return handle_tasks_stage(session, content_item, message, db)

    if not chunks:
        return {
            "stage": "explanation",
            "explanation_progress": next_index,
            "total_chunks": 0,
            "message": generate_module_explanation(content_item, session, 0.3, next_index, db),
        }

    explanation = generate_chunk_explanation(
        chunk_text=chunks[0],
        content_item=content_item,
        learner_id=session.learner_id,
        session_data=session_data,
        db=db,
        student_message=message if is_real_question else None,
    )
    session.explanation_progress = next_index + 1
    session_data["chunks_delivered_count"] = chunks_delivered + 1
    _save_session_data(session, session_data, db)

    total_chunks = len(get_ordered_chunks(content_item.item_id)) or len(chunks)
    return {
        "stage": "explanation",
        "explanation_progress": session.explanation_progress,
        "total_chunks": total_chunks,
        "message": explanation,
    }


def handle_tasks_stage(
    session: ModuleSession,
    content_item: ContentItem,
    message: Optional[str],
    db: Session,
) -> dict:
    session_data = _parse_session_data(session)

    if "recommended_resources" not in session_data:
        recs = get_recommendations_for_topic(
            learner_id=session.learner_id,
            topic=content_item.title,
            limit=2,
            db=db,
            exclude_content_item_id=content_item.item_id,
        )
        session_data["recommended_resources"] = recs
        _save_session_data(session, session_data, db)
        return {
            "stage": "tasks",
            "message": (
                "Great work! Based on this module, here are some resources to "
                "reinforce what you've learned:"
            ),
            "tasks": recs,
            "next_action": (
                "When you're ready, let me know and I'll start a short quiz to "
                "check your understanding."
            ),
        }

    if _classify_advance(message):
        session.stage = "quiz"
        session.updated_at = _now()
        db.commit()
        return handle_quiz_stage(session, content_item, message, db)

    return {
        "stage": "tasks",
        "message": (
            "Take your time with the resources above. Let me know when you're ready for the quiz."
        ),
        "tasks": session_data["recommended_resources"],
    }


def handle_quiz_stage(
    session: ModuleSession,
    content_item: ContentItem,
    message: Optional[str],
    db: Session,
) -> dict:
    del message
    session_data = _parse_session_data(session)

    if "quiz_id" not in session_data:
        quiz = generate_quiz_for_topic(
            learner_id=session.learner_id,
            topic=content_item.title,
            num_questions=5,
        )
        session_data["quiz_id"] = quiz["quiz_id"]
        _save_session_data(session, session_data, db)
        return {
            "stage": "quiz",
            "message": "Time for a quick quiz to check what you've learned!",
            "quiz_id": quiz["quiz_id"],
            "redirect_to_quiz": True,
            "topic": content_item.title,
        }

    return {
        "stage": "quiz",
        "quiz_id": session_data["quiz_id"],
        "redirect_to_quiz": True,
        "topic": content_item.title,
        "message": "Ready for your quiz? Click Start Quiz when you're set.",
    }


def start_or_resume_session(
    *,
    learner_id: str,
    content_item_id: str,
    db: Session,
) -> dict:
    session = db.scalars(
        select(ModuleSession).where(
            ModuleSession.learner_id == learner_id,
            ModuleSession.content_item_id == content_item_id,
        )
    ).first()

    content_item = db.get(ContentItem, content_item_id)
    if content_item is None:
        raise ValueError("Module not found")

    if session is None:
        session = ModuleSession(
            learner_id=learner_id,
            content_item_id=content_item_id,
            course_id=content_item.course_id,
            stage="onboarding",
            explanation_progress=0,
            session_data=json.dumps({}),
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        upsert_module_progress(
            db,
            learner_id=learner_id,
            content_item_id=content_item_id,
            percent_complete=10,
            status="in_progress",
        )

    if session.stage == "completed":
        return {
            "session_id": session.id,
            "stage": session.stage,
            "explanation_progress": session.explanation_progress,
            "message": "This module is complete. Return to curriculum for the next module.",
            "pdf_url": content_item.source_url,
        }

    if session.stage == "onboarding":
        mastery = get_topic_mastery(learner_id, content_item.title, db)
        return {
            "session_id": session.id,
            "stage": session.stage,
            "explanation_progress": session.explanation_progress,
            "message": generate_onboarding_message(content_item, mastery),
            "pdf_url": content_item.source_url,
        }

    if session.explanation_progress > 0 or session.stage not in {"onboarding", "explanation"}:
        session_data = _parse_session_data(session)
        if session.stage == "tasks":
            msg = "Welcome back! Review your recommended resources below, then say **ready** for the quiz."
            tasks = session_data.get("recommended_resources", [])
            return {
                "session_id": session.id,
                "stage": session.stage,
                "explanation_progress": session.explanation_progress,
                "message": msg,
                "pdf_url": content_item.source_url,
                "tasks": tasks,
            }
        if session.stage == "quiz":
            return {
                "session_id": session.id,
                "stage": session.stage,
                "explanation_progress": session.explanation_progress,
                "message": "Welcome back! You're ready for the module quiz.",
                "pdf_url": content_item.source_url,
                "quiz_id": session_data.get("quiz_id"),
                "redirect_to_quiz": True,
                "topic": content_item.title,
            }
        return {
            "session_id": session.id,
            "stage": session.stage,
            "explanation_progress": session.explanation_progress,
            "message": (
                f"Welcome back to **{content_item.title}**. "
                f"Say **next** to continue (part {session.explanation_progress + 1})."
            ),
            "pdf_url": content_item.source_url,
            "total_chunks": len(get_ordered_chunks(content_item.item_id)),
        }

    mastery = get_topic_mastery(learner_id, content_item.title, db)
    return {
        "session_id": session.id,
        "stage": session.stage,
        "explanation_progress": session.explanation_progress,
        "message": generate_onboarding_message(content_item, mastery),
        "pdf_url": content_item.source_url,
    }


def continue_session(
    *,
    session: ModuleSession,
    content_item: ContentItem,
    message: Optional[str],
    db: Session,
) -> dict:
    if session.stage == "onboarding":
        return handle_onboarding_stage(session, content_item, message, db)
    if session.stage == "explanation":
        return handle_explanation_stage(session, content_item, message, db)
    if session.stage == "tasks":
        return handle_tasks_stage(session, content_item, message, db)
    if session.stage == "quiz":
        return handle_quiz_stage(session, content_item, message, db)
    return {
        "stage": "completed",
        "message": "This module is complete. Return to curriculum to continue to the next module.",
    }


def complete_session(*, learner_id: str, session_id: str, db: Session) -> dict:
    session = db.scalars(
        select(ModuleSession).where(
            ModuleSession.id == session_id,
            ModuleSession.learner_id == learner_id,
        )
    ).first()
    if session is None:
        raise ValueError("Session not found")

    session.stage = "completed"
    session.updated_at = _now()
    db.commit()

    upsert_module_progress(
        db,
        learner_id=learner_id,
        content_item_id=session.content_item_id,
        percent_complete=100,
        status="completed",
    )

    next_module = None
    if session.course_id:
        all_modules = db.scalars(
            select(ContentItem)
            .where(
                ContentItem.course_id == session.course_id,
                ContentItem.status == "approved",
            )
            .order_by(ContentItem.module_order.asc().nullslast(), ContentItem.created_at.asc())
        ).all()
        current_idx = next(
            (i for i, m in enumerate(all_modules) if m.item_id == session.content_item_id),
            None,
        )
        if current_idx is not None and current_idx + 1 < len(all_modules):
            nxt = all_modules[current_idx + 1]
            next_module = {
                "content_item_id": nxt.item_id,
                "title": nxt.title,
                "module_number": current_idx + 2,
            }

    return {
        "message": "Module completed! Mastery updated based on your quiz performance.",
        "stage": "completed",
        "content_item_id": session.content_item_id,
        "next_module": next_module,
    }
