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
from fastapi_app.services.module_embedding_service import get_ordered_chunks
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
    "start quiz",
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


def _get_subject_context(content_item: ContentItem, db: Session) -> dict:
    """Course/department context so the LLM picks subject-appropriate examples."""
    from fastapi_app.admin.models import Course, Department

    course = None
    department_name = None
    if content_item.course_id:
        course = db.get(Course, content_item.course_id)
        if course and course.department_id:
            dept = db.get(Department, course.department_id)
            department_name = dept.name if dept else None

    return {
        "course_code": course.course_code if course else "",
        "course_title": course.course_title if course else "",
        "department": department_name or "General Studies",
        "module_title": content_item.title,
    }


def _get_topics_for_module(content_item: ContentItem, db: Session) -> List[dict]:
    """
    Returns topics for this module — reads cached topics.json from embed time.
    Lazy-computes and caches if missing (pre-feature content items).
    """
    from fastapi_app.services.module_embedding_service import (
        load_topics,
        save_topics,
        segment_module_topics,
    )

    cid = content_item.item_id
    record = db.get(ContentItem, cid)
    extracted_text = (record.extracted_text if record else None) or content_item.extracted_text or ""

    cached = load_topics(cid, extracted_text=extracted_text, db=db)
    if cached:
        return cached

    if extracted_text.strip():
        subject_ctx = _get_subject_context(content_item, db)
        payload = segment_module_topics(
            content_item_id=cid,
            extracted_text=extracted_text,
            module_title=content_item.title,
            course_title=subject_ctx.get("course_title", ""),
        )
        save_topics(cid, payload, db=db)
        topics = payload.get("topics", [])
        if topics:
            return topics

    chunks = get_ordered_chunks(cid)
    if chunks:
        return [{"title": f"Section {i + 1}", "content": c} for i, c in enumerate(chunks)]

    payload_json = content_item.payload_json or {}
    desc = str(payload_json.get("description") or payload_json.get("summary") or "")
    return [{"title": content_item.title, "content": desc or f"This module covers {content_item.title}."}]


_topics_for_content = _get_topics_for_module


def _create_linked_chat_session(learner_id: str, module_session_id: str, title: str) -> Optional[str]:
    from fastapi_app.services import sessions_service

    try:
        session = sessions_service.get_or_create_session(learner_id, subject=title)
        return session.get("session_id")
    except Exception:
        logger.exception("create_linked_chat_session_failed", extra={"module_session_id": module_session_id})
        return None


def _get_linked_session_id(session_data: dict) -> Optional[str]:
    return session_data.get("linked_chat_session_id")


def _append_to_chat_session(
    learner_id: str, session_data: dict, role: str, content: str
) -> None:
    from fastapi_app.services import sessions_service

    linked = _get_linked_session_id(session_data)
    if not linked or not content.strip():
        return
    try:
        if role == "assistant":
            sessions_service.touch_session(
                learner_id, linked, user_message="", assistant_message=content
            )
        else:
            sessions_service.touch_session(
                learner_id, linked, user_message=content, assistant_message=""
            )
    except Exception:
        logger.exception("append_to_chat_session_failed")


def _update_weekly_study_time(learner_id: str, minutes: int) -> None:
    if minutes <= 0:
        return
    try:
        runtime = get_runtime()
        profile = runtime.learner_memory.get_profile(learner_id)
        study = dict(profile.get("weekly_study") or {})
        study["minutes_studied"] = int(study.get("minutes_studied", 0) or 0) + minutes
        runtime.learner_memory.upsert_profile(learner_id, {"weekly_study": study})
    except Exception:
        logger.exception("update_weekly_study_time_failed")


def get_weekly_study_stats(learner_id: str) -> dict:
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    prefs = profile.get("preferences") or {}
    step4 = (profile.get("onboarding") or {}).get("step4") or prefs
    goal_hours = float(step4.get("weekly_hours") or prefs.get("weekly_hours") or 0)
    study = profile.get("weekly_study") or {}
    completed_minutes = int(study.get("minutes_studied", 0) or 0)
    completed_hours = round(completed_minutes / 60, 1)
    percent = min(100, int((completed_hours / goal_hours) * 100)) if goal_hours > 0 else 0
    return {
        "weekly_goal_hours": goal_hours,
        "completed_hours": completed_hours,
        "percent": percent,
        "message": (
            f"{completed_hours}h of {goal_hours}h completed this week"
            if goal_hours > 0
            else "Set a weekly goal in Settings"
        ),
    }


def _find_next_module(session: ModuleSession, db: Session) -> Optional[dict]:
    if not session.course_id:
        return None
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
        return {
            "content_item_id": nxt.item_id,
            "title": nxt.title,
            "module_number": current_idx + 2,
        }
    return None


def _recalibrate_if_needed(message: Optional[str], session_data: dict, learner_id: str) -> dict:
    if not message:
        session_data.pop("temporary_simplify", None)
        return session_data

    current_level = session_data.get("onboarding_level", "beginner")
    comprehension_scores = session_data.get("comprehension_scores", [])
    lower = message.lower()

    sophisticated_signals = [
        "why does", "what's the reason", "compare", "distinguish", "critically",
        "exception to", "limitation of", "what if", "what about", "how does this relate",
    ]
    if any(sig in lower for sig in sophisticated_signals):
        level_upgrade = {
            "beginner": "aware",
            "aware": "intermediate",
            "intermediate": "advanced",
            "advanced": "advanced",
        }
        new_level = level_upgrade.get(current_level, current_level)
        if new_level != current_level:
            session_data["onboarding_level"] = new_level
            session_data["auto_upgraded"] = True

    if len(comprehension_scores) >= 2:
        avg_score = sum(comprehension_scores[-2:]) / 2
        if avg_score >= 85 and current_level in ("beginner", "aware"):
            session_data["onboarding_level"] = "intermediate"
            session_data["auto_upgraded"] = True
        elif avg_score < 50 and current_level in ("intermediate", "advanced"):
            level_downgrade = {"advanced": "intermediate", "intermediate": "aware"}
            session_data["onboarding_level"] = level_downgrade.get(current_level, current_level)

    confusion_signals = [
        "i don't understand", "confused", "what does that mean",
        "can you explain", "i'm lost", "huh", "??",
    ]
    if any(sig in lower for sig in confusion_signals):
        session_data["temporary_simplify"] = True
    else:
        session_data.pop("temporary_simplify", None)

    return session_data


def _parse_onboarding_style_level(message: str) -> tuple[str, str]:
    raw = message.lower().strip()
    if "b" in raw or "framework" in raw or "structured" in raw or "principle" in raw:
        style = "structured_framework"
    elif "c" in raw or "story" in raw or "scenario" in raw:
        style = "scenario_first"
    elif "d" in raw or "exam" in raw or "marks" in raw or "examiner" in raw:
        style = "exam_technique"
    elif "e" in raw or "quick" in raw or "bullet" in raw or "fast" in raw:
        style = "quick_drill"
    elif "f" in raw or "deep" in raw or "detailed" in raw or "comparison" in raw:
        style = "deep_detailed"
    elif "g" in raw or "question" in raw or "guide me" in raw or "socratic" in raw:
        style = "socratic"
    elif "h" in raw or "something else" in raw:
        style = "conversational"
    elif "a" in raw or "step" in raw or "break" in raw:
        style = "step_by_step"
    else:
        style = "step_by_step"

    if "completely" in raw or ("new" in raw and "never" in raw):
        level = "beginner"
    elif "heard" in raw or ("class" in raw and "b" in raw):
        level = "aware"
    elif "basics" in raw or "deeper" in raw:
        level = "intermediate"
    elif "well" in raw or "reinforce" in raw or "advanced" in raw:
        level = "advanced"
    else:
        level = "beginner"
    return style, level


ONBOARDING_STYLE_OPTIONS = [
    {"id": "step_by_step", "label": "Step by step",
     "description": "Break down every key point with real-world examples"},
    {"id": "structured_framework", "label": "Structured framework",
     "description": "Clear problem → principle → application → outcome structure"},
    {"id": "scenario_first", "label": "Story or scenario first",
     "description": "Open with a real-world situation, concept unfolds through it"},
    {"id": "exam_technique", "label": "Exam-focused",
     "description": "Key points, common mistakes, how to score full marks"},
    {"id": "quick_drill", "label": "Quick summary + test me",
     "description": "Bullet points then immediate questions"},
    {"id": "deep_detailed", "label": "Deep and detailed",
     "description": "Beyond the notes — debates, comparisons, expert viewpoints"},
    {"id": "socratic", "label": "Ask me questions",
     "description": "Guide me to figure it out myself"},
    {"id": "custom", "label": "Something else",
     "description": "Describe how you like to learn"},
]

ONBOARDING_LEVEL_OPTIONS = [
    {"id": "beginner", "label": "Completely new",
     "description": "Never studied this"},
    {"id": "aware", "label": "Heard of it",
     "description": "Heard of it in class but don't really understand it"},
    {"id": "intermediate", "label": "Know the basics",
     "description": "Need a deeper understanding"},
    {"id": "advanced", "label": "Know it well",
     "description": "Just reinforcing for exams"},
]


def generate_onboarding_message(
    content_item: ContentItem, mastery: float, subject_ctx: Optional[dict] = None
) -> dict:
    """Structured onboarding payload for the first question (teaching style)."""
    del mastery, subject_ctx
    topic = content_item.title
    return {
        "message": (
            f"Welcome to **{topic}**! To teach you in the way that works best for you, "
            "let's start with a quick question."
        ),
        "onboarding_step": "style",
        "options": ONBOARDING_STYLE_OPTIONS,
        "question": "How do you want me to explain things?",
    }


def generate_level_question(content_item: ContentItem) -> dict:
    """Structured onboarding payload for the second question (familiarity)."""
    topic = content_item.title
    return {
        "message": "Got it. One more thing —",
        "onboarding_step": "level",
        "options": ONBOARDING_LEVEL_OPTIONS,
        "question": f"How familiar are you with **{topic}** right now?",
    }


def handle_onboarding_selection(
    session: ModuleSession,
    content_item: ContentItem,
    selected_option_id: str,
    db: Session,
) -> dict:
    """Handles a tapped onboarding option."""
    session_data = _parse_session_data(session)
    current_step = session_data.get("onboarding_step", "style")

    if current_step == "style":
        if selected_option_id == "custom":
            session_data["onboarding_step"] = "style_custom_pending"
            _save_session_data(session, session_data, db)
            return {
                "stage": "onboarding",
                "onboarding_step": "style_custom_input",
                "message": "Sure — describe how you like to learn and I'll adapt to it.",
                "awaiting_custom_text": True,
            }

        valid_ids = {o["id"] for o in ONBOARDING_STYLE_OPTIONS}
        style = selected_option_id if selected_option_id in valid_ids else "step_by_step"
        session_data["onboarding_style"] = style
        session_data["onboarding_step"] = "level"
        _save_session_data(session, session_data, db)

        level_q = generate_level_question(content_item)
        return {"stage": "onboarding", **level_q}

    if current_step == "level":
        valid_ids = {o["id"] for o in ONBOARDING_LEVEL_OPTIONS}
        level = selected_option_id if selected_option_id in valid_ids else "beginner"
        session_data["onboarding_level"] = level
        _save_session_data(session, session_data, db)
        return _complete_onboarding(session, content_item, session_data, db)

    return {"stage": "onboarding", "message": "Let's continue.", "options": []}


def handle_onboarding_custom_text(
    session: ModuleSession,
    content_item: ContentItem,
    message: str,
    db: Session,
) -> dict:
    """Handles free-text after 'Something else' or typed fallback."""
    session_data = _parse_session_data(session)
    session_data["onboarding_style"] = "custom"
    session_data["onboarding_style_custom_description"] = message.strip()
    session_data["onboarding_step"] = "level"
    _save_session_data(session, session_data, db)

    level_q = generate_level_question(content_item)
    return {"stage": "onboarding", **level_q}


def _complete_onboarding(
    session: ModuleSession,
    content_item: ContentItem,
    session_data: dict,
    db: Session,
) -> dict:
    """Called once both style and level are captured. Delivers first topic."""
    subject_ctx = _get_subject_context(content_item, db)

    session_data["topic_index"] = 0
    session_data.setdefault("chunks_delivered_count", 0)
    session_data.setdefault("topics_covered", [])
    session_data.setdefault("comprehension_scores", [])
    session.stage = "explanation"
    session.updated_at = _now()

    style = session_data.get("onboarding_style", "step_by_step")
    level = session_data.get("onboarding_level", "beginner")

    style_ack = {
        "step_by_step": "I'll break everything down step by step with real-world examples.",
        "structured_framework": "I'll use a clear structured framework for every concept.",
        "scenario_first": "I'll lead with real scenarios, then connect them to the concepts.",
        "exam_technique": "I'll focus on exactly what's needed to score well.",
        "quick_drill": "I'll keep it concise — bullet points, then quick tests.",
        "deep_detailed": "I'll go beyond the notes with deeper detail and comparisons.",
        "socratic": "I'll guide you with questions so you work things out yourself.",
        "custom": "Got it — I'll teach the way you described.",
    }
    level_ack = {
        "beginner": "Since this is new to you, I'll start from the very beginning.",
        "aware": "You've heard of this before, so I'll build on what you already know.",
        "intermediate": "I'll focus on deepening your understanding rather than basics.",
        "advanced": "I'll focus on nuance and what matters most for assessment.",
    }
    ack = f"{style_ack.get(style, style_ack['step_by_step'])} {level_ack.get(level, level_ack['beginner'])}\n\nLet's begin."

    first_explanation = _deliver_topic(
        topic_index=0,
        content_item=content_item,
        session_data=session_data,
        student_message="",
        learner_id=session.learner_id,
        subject_ctx=subject_ctx,
        db=db,
    )
    full_message = ack + "\n\n---\n\n" + first_explanation

    session_data["chunks_delivered_count"] = 1
    session_data["topic_index"] = 1
    topics = _topics_for_content(content_item, db)
    if topics:
        session_data.setdefault("topics_covered", []).append(topics[0]["title"])
    session.explanation_progress = 1
    _save_session_data(session, session_data, db)
    _append_to_chat_session(session.learner_id, session_data, "assistant", full_message)

    return {
        "stage": "explanation",
        "message": full_message,
        "explanation_progress": 1,
        "total_topics": len(topics),
    }


def _onboarding_resume_payload(session: ModuleSession, content_item: ContentItem, db: Session) -> dict:
    """Return the correct structured onboarding question when resuming."""
    session_data = _parse_session_data(session)
    onb_step = session_data.get("onboarding_step", "style")

    if onb_step == "style_custom_pending":
        return {
            "stage": "onboarding",
            "onboarding_step": "style_custom_input",
            "message": "Sure — describe how you like to learn and I'll adapt to it.",
            "awaiting_custom_text": True,
        }

    if session_data.get("onboarding_style") and not session_data.get("onboarding_level"):
        level_q = generate_level_question(content_item)
        return {"stage": "onboarding", **level_q}

    mastery = get_topic_mastery(session.learner_id, content_item.title, db)
    subject_ctx = _get_subject_context(content_item, db)
    payload = generate_onboarding_message(content_item, mastery, subject_ctx)
    return {"stage": "onboarding", **payload}


def _deliver_topic(
    *,
    topic_index: int,
    content_item: ContentItem,
    session_data: dict,
    student_message: str,
    learner_id: str,
    subject_ctx: dict,
    db: Session,
) -> str:
    topics = _topics_for_content(content_item, db)
    idx = min(topic_index, len(topics) - 1)
    topic = topics[idx]
    total = len(topics)

    style = session_data.get("onboarding_style", "step_by_step")
    level = session_data.get("onboarding_level", "beginner")
    _, primary_goal = _get_learner_preferences(learner_id)

    style_instructions = {
        "step_by_step": (
            "Take each key sentence or idea from the content. Quote or restate it, "
            "then explain in plain language. After each point, give a real-world example "
            "appropriate to this subject and Nigerian context (infer from the department — "
            "do not default to legal examples unless this is a Law course)."
        ),
        "structured_framework": (
            "Use a clear structured framework appropriate to this subject. "
            "Pick whichever structure naturally fits the department: e.g. for Law-type subjects "
            "Issue → Rule → Application → Conclusion; for Business Situation → Problem → "
            "Solution → Outcome; for Religious/Fiqh Principle → Evidence → Application → "
            "Ruling; for Language Rule → Pattern → Example → Practice. "
            f"Choose what fits {subject_ctx['department']} best."
        ),
        "scenario_first": (
            "Open with a realistic, relatable scenario appropriate to the subject and "
            "Nigerian context. Let the concept emerge through the scenario, then name the "
            "underlying principle."
        ),
        "exam_technique": (
            "Focus on assessment performance: key point precisely, references from content, "
            "concise answer format, common mistakes on this topic."
        ),
        "quick_drill": (
            "Concise: 3-5 bullet points. After bullets, one immediate test question. "
            "Under 200 words total."
        ),
        "deep_detailed": (
            "Go beyond surface content: nuance, alternative views, connections to related concepts."
        ),
        "socratic": (
            "Do NOT explain directly. Ask 2-3 guiding questions, then confirm or correct."
        ),
        "custom": (
            "Talk naturally and adapt to the student's described learning preference. "
            f"Preference: {session_data.get('onboarding_style_custom_description', 'flexible approach')}"
        ),
    }

    depth_instructions = {
        "beginner": "Assume zero prior knowledge. Define every key term clearly.",
        "aware": "Assume they've heard the terms. Focus on what they mean in practice.",
        "intermediate": "Skip basic definitions. Focus on application and nuance.",
        "advanced": "Go deep: edge cases, confusions, assessment-critical points.",
    }

    goal_note = (
        "\nThis student's goal is Academic Excellence — flag assessment-critical points."
        if primary_goal == "Academic Excellence"
        else ""
    )

    address_question = ""
    if student_message and len(student_message.strip()) > 8 and not _classify_advance(student_message):
        address_question = (
            f'\n\nThe student asked or said: "{student_message}". '
            "Address this first before continuing."
        )

    simplify_note = ""
    if session_data.get("temporary_simplify"):
        simplify_note = (
            "\nIMPORTANT: The student expressed confusion. Simplify — shorter sentences, "
            "more relatable examples."
        )

    grounding = (
        "\n\nCRITICAL: Base your explanation ONLY on the content provided below. "
        "Do NOT invent facts, sources, or rules not in the content. "
        "Illustrative examples must be clearly illustrative unless the content names a real case. "
        "If asked something outside this content, say it is beyond this module's material."
    )

    next_label = topics[idx + 1]["title"] if idx + 1 < total else "the tasks"
    prompt = f"""You are an AI tutor at Fountain University, Osogbo, Nigeria.
Teaching a {subject_ctx['department']} student one-on-one.

COURSE: {subject_ctx['course_code']} — {subject_ctx['course_title']}
MODULE: {content_item.title}
TOPIC {idx + 1} of {total}: {topic['title']}

CONTENT TO TEACH:
{topic['content']}

TEACHING STYLE: {style_instructions.get(style, style_instructions['step_by_step'])}
DEPTH: {depth_instructions.get(level, depth_instructions['beginner'])}{goal_note}{address_question}{simplify_note}{grounding}

REQUIRED OUTPUT FORMAT:
1. Start with: "📚 **Topic {idx + 1} of {total}: {topic['title']}**"
2. Follow the style instruction
3. Use Nigerian-relevant examples that fit {subject_ctx['department']} specifically
4. End with EXACTLY:
   "---\\n✅ That's **{topic['title']}** covered. Ask any questions, or say **'next'** to continue to {next_label}."

Keep under 400 words. Use markdown."""

    return _call_llm(prompt) or (
        f"📚 **Topic {idx + 1} of {total}: {topic['title']}**\n\n"
        f"{topic['content'][:800]}…\n\n---\n✅ Say **'next'** to continue."
    )


def _generate_comprehension_check(
    topic: dict, subject_ctx: dict, session_data: dict
) -> str:
    level = session_data.get("onboarding_level", "beginner")
    question_type = (
        "explain in your own words"
        if level in ("beginner", "aware")
        else "apply to a real situation"
    )
    prompt = f"""Generate ONE typed comprehension question for a {subject_ctx['department']} student.

COURSE: {subject_ctx['course_title']}
TOPIC: {topic['title']}
CONTENT SUMMARY: {topic['content'][:600]}

Question type: {question_type}
Level: {level}

Format:
**Quick Check ✏️**
[Your question — 2-3 sentences, Nigerian context appropriate to the subject]

*(Type your answer — I'll give you feedback)*"""

    return _call_llm(prompt) or (
        f"**Quick Check ✏️**\nIn your own words, explain the main idea of **{topic['title']}**."
    )


def _grade_comprehension_response(
    student_answer: str,
    topic: dict,
    subject_ctx: dict,
) -> dict:
    prompt = f"""Grade this {subject_ctx['department']} student's typed answer.

COURSE: {subject_ctx['course_title']}
TOPIC: {topic['title']}
CORRECT CONTENT: {topic['content'][:800]}

STUDENT'S ANSWER: "{student_answer}"

Return EXACTLY:
SCORE: [0-100]
FEEDBACK: [2-4 sentences. Encouraging. End with "Say 'next' to continue." if score >= 70]"""

    raw = _call_llm(prompt)
    score_match = re.search(r"SCORE:\s*(\d+)", raw or "")
    score = int(score_match.group(1)) if score_match else 60
    feedback_match = re.search(r"FEEDBACK:\s*(.*)", raw or "", re.DOTALL)
    feedback = feedback_match.group(1).strip() if feedback_match else (raw or "Good effort. Say 'next' to continue.")
    return {"score": score, "feedback": feedback}


def generate_module_explanation(
    content_item: ContentItem,
    session: ModuleSession,
    mastery: float,
    chunk_index: int,
    db: Session,
) -> str:
    """Legacy fallback when topic delivery is unavailable."""
    del mastery, chunk_index
    subject_ctx = _get_subject_context(content_item, db)
    session_data = _parse_session_data(session)
    return _deliver_topic(
        topic_index=0,
        content_item=content_item,
        session_data=session_data,
        student_message="",
        learner_id=session.learner_id,
        subject_ctx=subject_ctx,
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

    q = urllib.parse.quote(f"{topic} explained Nigeria")
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
    selected_option_id: Optional[str] = None,
) -> dict:
    session_data = _parse_session_data(session)
    onb_step = session_data.get("onboarding_step", "style")

    if onb_step == "style_custom_pending" and message and message.strip():
        return handle_onboarding_custom_text(session, content_item, message.strip(), db)

    if selected_option_id:
        return handle_onboarding_selection(session, content_item, selected_option_id, db)

    if message and message.strip() and not session_data.get("onboarding_style"):
        return handle_onboarding_custom_text(session, content_item, message.strip(), db)

    return _onboarding_resume_payload(session, content_item, db)


def handle_explanation_stage(
    session: ModuleSession,
    content_item: ContentItem,
    message: Optional[str],
    db: Session,
) -> dict:
    session_data = _parse_session_data(session)
    subject_ctx = _get_subject_context(content_item, db)
    session_data = _recalibrate_if_needed(message, session_data, session.learner_id)

    chunks_delivered = int(session_data.get("chunks_delivered_count", 0))
    topic_index = int(session_data.get("topic_index", 0))
    topics = _topics_for_content(content_item, db)
    total_topics = max(len(topics), 1)

    should_advance_to_tasks = (
        chunks_delivered > 0
        and (topic_index >= total_topics or _classify_advance(message))
    )
    if should_advance_to_tasks:
        session.stage = "tasks"
        session.updated_at = _now()
        _save_session_data(session, session_data, db)
        return handle_tasks_stage(session, content_item, message, db)

    if (
        chunks_delivered > 0
        and chunks_delivered % 2 == 0
        and not _classify_advance(message)
        and (not message or len(message.strip()) < 5)
        and not session_data.get(f"check_done_{chunks_delivered}", False)
    ):
        check_topic = topics[max(0, topic_index - 1)] if topics else {"title": content_item.title, "content": ""}
        check = _generate_comprehension_check(check_topic, subject_ctx, session_data)
        session_data[f"check_done_{chunks_delivered}"] = True
        session_data["awaiting_check_response"] = True
        _save_session_data(session, session_data, db)
        _append_to_chat_session(session.learner_id, session_data, "assistant", check)
        return {
            "stage": "explanation",
            "message": check,
            "explanation_progress": topic_index,
            "total_topics": total_topics,
            "is_comprehension_check": True,
        }

    if session_data.get("awaiting_check_response") and message and len(message.strip()) > 5:
        check_topic = topics[max(0, topic_index - 2)] if topics else {"title": content_item.title, "content": ""}
        grade_response = _grade_comprehension_response(message.strip(), check_topic, subject_ctx)
        session_data["awaiting_check_response"] = False
        scores = session_data.get("comprehension_scores", [])
        scores.append(grade_response["score"])
        session_data["comprehension_scores"] = scores
        _save_session_data(session, session_data, db)
        _append_to_chat_session(session.learner_id, session_data, "assistant", grade_response["feedback"])
        return {
            "stage": "explanation",
            "message": grade_response["feedback"],
            "score": grade_response["score"],
            "explanation_progress": topic_index,
            "total_topics": total_topics,
        }

    explanation = _deliver_topic(
        topic_index=topic_index,
        content_item=content_item,
        session_data=session_data,
        student_message=message or "",
        learner_id=session.learner_id,
        subject_ctx=subject_ctx,
        db=db,
    )

    session_data["chunks_delivered_count"] = chunks_delivered + 1
    session_data["topic_index"] = topic_index + 1
    if topic_index < len(topics):
        covered = session_data.get("topics_covered", [])
        covered.append(topics[topic_index]["title"])
        session_data["topics_covered"] = covered
    session.explanation_progress = topic_index + 1
    _save_session_data(session, session_data, db)
    _append_to_chat_session(session.learner_id, session_data, "assistant", explanation)

    return {
        "stage": "explanation",
        "explanation_progress": topic_index + 1,
        "total_topics": total_topics,
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
    subject_ctx = _get_subject_context(content_item, db)

    if "quiz_id" not in session_data:
        from fastapi_app.services.quiz_ai_service import generate_mixed_quiz

        topics_covered = session_data.get("topics_covered", [])
        all_topics = _get_topics_for_module(content_item, db)
        extracted_text = content_item.extracted_text or ""
        covered_content = "\n\n".join(
            t["content"] for t in all_topics if t["title"] in topics_covered
        ) or extracted_text[:2000] or content_item.title

        quiz = generate_mixed_quiz(
            subject_ctx=subject_ctx,
            content=covered_content,
            num_mcq=3,
            num_short_answer=2,
        )
        import uuid as _uuid

        quiz_id = str(_uuid.uuid4())[:8]
        session_data["quiz_id"] = quiz_id
        session_data["quiz_data"] = quiz
        _save_session_data(session, session_data, db)

        return {
            "stage": "quiz",
            "message": (
                "Time for a quiz! **3 multiple choice** and **2 short answer** "
                "questions where you type your understanding.\n\n"
                "Short answers are AI-graded — no single right wording, "
                "just show you understand the concept."
            ),
            "quiz_id": quiz_id,
            "quiz_data": quiz,
            "redirect_to_quiz": True,
            "topic": content_item.title,
        }

    return {
        "stage": "quiz",
        "quiz_id": session_data["quiz_id"],
        "quiz_data": session_data.get("quiz_data"),
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
    content_item = db.get(ContentItem, content_item_id)
    if content_item is None:
        raise ValueError("Module not found")

    subject_ctx = _get_subject_context(content_item, db)
    mastery = get_topic_mastery(learner_id, content_item.title, db)

    session = db.scalars(
        select(ModuleSession).where(
            ModuleSession.learner_id == learner_id,
            ModuleSession.content_item_id == content_item_id,
        )
    ).first()

    if session is None:
        session_data = {
            "chunks_delivered_count": 0,
            "onboarding_style": "",
            "onboarding_level": "",
            "onboarding_step": "style",
            "topic_index": 0,
            "topics_covered": [],
            "comprehension_scores": [],
            "recommended_resources": None,
            "quiz_id": None,
            "session_start_ts": _now().isoformat(),
        }
        session = ModuleSession(
            learner_id=learner_id,
            content_item_id=content_item_id,
            course_id=content_item.course_id,
            stage="onboarding",
            explanation_progress=0,
            session_data=json.dumps(session_data),
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        chat_session_id = _create_linked_chat_session(
            learner_id, session.id, content_item.title
        )
        if chat_session_id:
            session_data["linked_chat_session_id"] = chat_session_id
            session.session_data = json.dumps(session_data)
            db.commit()

        upsert_module_progress(
            db,
            learner_id=learner_id,
            content_item_id=content_item_id,
            percent_complete=10,
            status="in_progress",
        )

        onboarding_payload = generate_onboarding_message(content_item, mastery, subject_ctx)
        return {
            "session_id": session.id,
            "stage": "onboarding",
            "explanation_progress": 0,
            **onboarding_payload,
            "pdf_url": content_item.source_url,
        }

    session_data = _parse_session_data(session)
    chunks_delivered = int(session_data.get("chunks_delivered_count", 0))
    topics = _topics_for_content(content_item, db)
    total_topics = max(len(topics), 1)

    if chunks_delivered < 2 and session.stage not in ("completed",):
        session.stage = "onboarding"
        session.explanation_progress = 0
        session_data["chunks_delivered_count"] = 0
        session_data["topic_index"] = 0
        session_data["onboarding_step"] = "style"
        session_data["onboarding_style"] = ""
        session_data["onboarding_level"] = ""
        session_data["recommended_resources"] = None
        session_data["quiz_id"] = None
        session_data.pop("quiz_data", None)
        session.session_data = json.dumps(session_data)
        session.updated_at = _now()
        db.commit()
        onboarding_payload = generate_onboarding_message(content_item, mastery, subject_ctx)
        return {
            "session_id": session.id,
            "stage": "onboarding",
            "explanation_progress": 0,
            **onboarding_payload,
            "pdf_url": content_item.source_url,
        }

    if session.stage == "onboarding":
        resume_onboarding = _onboarding_resume_payload(session, content_item, db)
        return {
            "session_id": session.id,
            **resume_onboarding,
            "explanation_progress": session.explanation_progress,
            "pdf_url": content_item.source_url,
        }

    if session.stage == "completed":
        return {
            "session_id": session.id,
            "stage": "completed",
            "explanation_progress": session.explanation_progress,
            "message": (
                f"You've completed **{content_item.title}**. "
                "Head back to curriculum for the next module."
            ),
            "pdf_url": content_item.source_url,
        }

    resume_messages = {
        "explanation": (
            f"Welcome back to **{content_item.title}**! "
            f"You've covered {chunks_delivered} topic(s) so far. "
            "Say **'next'** to continue, or ask any question."
        ),
        "tasks": (
            f"You're in the tasks stage for **{content_item.title}**. "
            "Review the resources below, then say **'ready'** for the quiz."
        ),
        "quiz": (
            f"You were about to take the quiz for **{content_item.title}**. "
            "Say **'start quiz'** when ready."
        ),
    }

    result: dict = {
        "session_id": session.id,
        "stage": session.stage,
        "explanation_progress": session.explanation_progress,
        "message": resume_messages.get(session.stage, "Welcome back!"),
        "pdf_url": content_item.source_url,
        "total_topics": total_topics,
    }

    if session.stage == "tasks":
        result["tasks"] = session_data.get("recommended_resources", [])
    if session.stage == "quiz":
        result["quiz_id"] = session_data.get("quiz_id")
        result["quiz_data"] = session_data.get("quiz_data")
        result["redirect_to_quiz"] = True
        result["topic"] = content_item.title

    return result


def continue_session(
    *,
    session: ModuleSession,
    content_item: ContentItem,
    message: Optional[str],
    db: Session,
    selected_option_id: Optional[str] = None,
) -> dict:
    if session.stage == "onboarding":
        return handle_onboarding_stage(
            session, content_item, message, db, selected_option_id=selected_option_id
        )
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

    session_data = _parse_session_data(session)
    chunks_delivered = int(session_data.get("chunks_delivered_count", 0))

    if chunks_delivered < 2:
        upsert_module_progress(
            db,
            learner_id=learner_id,
            content_item_id=session.content_item_id,
            percent_complete=40,
            status="in_progress",
        )
        return {
            "message": (
                "Quiz recorded! To fully complete this module, go through the "
                "AI explanation first — click 'Continue' on the curriculum."
            ),
            "stage": "quiz_only",
            "content_item_id": session.content_item_id,
            "next_module": None,
        }

    session.stage = "completed"
    session.updated_at = _now()
    db.commit()

    topics_covered = len(session_data.get("topics_covered", []))
    content_item = db.get(ContentItem, session.content_item_id)
    all_topics = _get_topics_for_module(content_item, db) if content_item else []
    total_topics = max(len(all_topics), 1)
    coverage_pct = min(100, int((topics_covered / total_topics) * 80) + 20)

    upsert_module_progress(
        db,
        learner_id=learner_id,
        content_item_id=session.content_item_id,
        percent_complete=coverage_pct,
        status="completed" if coverage_pct >= 90 else "in_progress",
    )

    start_ts = session_data.get("session_start_ts")
    if start_ts:
        try:
            start = datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
            elapsed_minutes = int((_now() - start).total_seconds() / 60)
            if elapsed_minutes > 0:
                session_data["time_spent_minutes"] = elapsed_minutes
                session.session_data = json.dumps(session_data)
                db.commit()
                _update_weekly_study_time(learner_id, elapsed_minutes)
        except (ValueError, TypeError):
            pass

    next_module = _find_next_module(session, db)

    return {
        "message": "Module completed! Great work.",
        "stage": "completed",
        "content_item_id": session.content_item_id,
        "next_module": next_module,
        "topics_covered": topics_covered,
        "total_topics": total_topics,
        "coverage_percent": coverage_pct,
    }
