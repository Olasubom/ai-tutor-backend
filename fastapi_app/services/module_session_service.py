"""Module session state machine: explanation → tasks → quiz → completed."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.core.context import get_runtime
from agency.core.tools.models import ContentItem, ModuleSession
from agency.tutor_service import handle_recommend_request
from fastapi_app.services.module_embedding_service import get_ordered_chunks, retrieve_relevant_chunks
from fastapi_app.services.module_progress_service import upsert_module_progress
from fastapi_app.services import quiz_service

logger = logging.getLogger(__name__)

_READY_KEYWORDS = re.compile(
    r"\b(yes|yeah|yep|next|got it|understand|understood|ready|continue|proceed|move on|done|finished|ok|okay)\b",
    re.IGNORECASE,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _openai_client() -> Optional[OpenAI]:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or "your_key" in key.lower():
        return None
    return OpenAI(api_key=key)


def get_topic_mastery(learner_id: str, topic: str, db: Session) -> float:
    del db
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    state = profile.get("topic_mastery", {}).get(topic, {})
    return float(state.get("p_l", 0.3))


def classify_ready_to_advance(message: Optional[str]) -> bool:
    if not message or not message.strip():
        return False
    if _READY_KEYWORDS.search(message.strip()):
        return True
    client = _openai_client()
    if not client:
        return False
    try:
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You classify whether a student wants to move to the next stage. "
                        'Reply with exactly "yes" or "no".'
                    ),
                },
                {
                    "role": "user",
                    "content": f"Student message: {message}\nAre they ready to move on?",
                },
            ],
            temperature=0,
            max_tokens=5,
        )
        answer = (resp.choices[0].message.content or "").strip().lower()
        return answer.startswith("yes")
    except Exception:
        logger.exception("classify_ready_to_advance_failed")
        return False


def generate_chunk_explanation(
    *,
    chunk_text: str,
    content_item: ContentItem,
    learner_id: str,
    db: Session,
    user_message: Optional[str] = None,
) -> str:
    mastery = get_topic_mastery(learner_id, content_item.title, db)
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    prefs = profile.get("learning_preferences", {})
    depth = "simple, step-by-step" if mastery < 0.4 else "moderate detail" if mastery < 0.7 else "advanced"

    rag_context = retrieve_relevant_chunks(content_item.item_id, chunk_text[:500], top_k=3)
    context_block = "\n\n".join(rag_context) if rag_context else chunk_text

    prompt = (
        f"You are an AI tutor explaining module content: '{content_item.title}'.\n"
        f"Student mastery on this topic: {int(mastery * 100)}%. Use {depth} language.\n"
        f"Learning preferences: {json.dumps(prefs, default=str)}\n\n"
        f"Source material excerpt:\n{context_block}\n\n"
    )
    if user_message:
        prompt += f"Student just said: {user_message}\n\n"
    prompt += (
        "Explain the key ideas sentence-by-sentence with real-world examples "
        "(include Nigerian and global contexts where helpful). "
        "Use markdown headings and bullet points. End by asking if they want the next part."
    )

    client = _openai_client()
    if client:
        try:
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[
                    {"role": "system", "content": "You are a warm, clear academic tutor."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.6,
            )
            text = (resp.choices[0].message.content or "").strip()
            if text:
                return text
        except Exception:
            logger.exception("generate_chunk_explanation_failed")

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
        db=db,
    )


def get_recommendations_for_topic(
    *,
    learner_id: str,
    topic: str,
    limit: int,
    db: Session,
) -> List[Dict[str, Any]]:
    del db
    result = handle_recommend_request(
        learner_id=learner_id,
        message=f"Recommend {limit} supplementary resources for the topic: {topic}",
        course_context={"subject": topic},
        limit=limit,
        use_agent=False,
    )
    return list(result.get("recommendations", []))[:limit]


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


def handle_explanation_stage(
    session: ModuleSession,
    content_item: ContentItem,
    message: Optional[str],
    db: Session,
) -> dict:
    chunks = get_ordered_chunks(content_item.item_id)
    if not chunks:
        chunks = retrieve_relevant_chunks(content_item.item_id, content_item.title or "", top_k=10)

    next_index = session.explanation_progress
    should_advance = (len(chunks) > 0 and next_index >= len(chunks)) or classify_ready_to_advance(message)

    if should_advance and len(chunks) == 0 and not classify_ready_to_advance(message):
        should_advance = False

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

    chunk_text = chunks[min(next_index, len(chunks) - 1)]
    explanation = generate_chunk_explanation(
        chunk_text=chunk_text,
        content_item=content_item,
        learner_id=session.learner_id,
        db=db,
        user_message=message,
    )
    session.explanation_progress = next_index + 1
    session.updated_at = _now()
    db.commit()

    return {
        "stage": "explanation",
        "explanation_progress": session.explanation_progress,
        "total_chunks": len(chunks),
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

    if classify_ready_to_advance(message):
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
            stage="explanation",
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

    mastery = get_topic_mastery(learner_id, content_item.title, db)

    if session.stage == "completed":
        return {
            "session_id": session.id,
            "stage": session.stage,
            "explanation_progress": session.explanation_progress,
            "message": "This module is complete. Return to curriculum for the next module.",
            "pdf_url": content_item.source_url,
        }

    if session.explanation_progress > 0 or session.stage != "explanation":
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

    first_message = generate_module_explanation(
        content_item, session, mastery, chunk_index=0, db=db
    )
    if get_ordered_chunks(content_item.item_id) or retrieve_relevant_chunks(
        content_item.item_id, content_item.title or "", top_k=1
    ):
        session.explanation_progress = 1
        session.updated_at = _now()
        db.commit()

    return {
        "session_id": session.id,
        "stage": session.stage,
        "explanation_progress": session.explanation_progress,
        "message": first_message,
        "pdf_url": content_item.source_url,
        "total_chunks": len(get_ordered_chunks(content_item.item_id)),
    }


def continue_session(
    *,
    session: ModuleSession,
    content_item: ContentItem,
    message: Optional[str],
    db: Session,
) -> dict:
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

    return {
        "message": "Module completed! Mastery updated based on your quiz performance.",
        "stage": "completed",
        "content_item_id": session.content_item_id,
    }
