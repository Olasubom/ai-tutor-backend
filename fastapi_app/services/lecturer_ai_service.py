"""LLM-backed teaching assistant for lecturers."""

from __future__ import annotations

import os
from typing import Optional

from openai import OpenAI
from sqlalchemy.orm import Session

from fastapi_app.admin.models import Course
from fastapi_app.auth.models import User
from fastapi_app.services.enrollment_service import list_course_students
from fastapi_app.services.lecturer_course_service import assert_lecturer_owns_course


def _openai_client() -> Optional[OpenAI]:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or "your_key" in key.lower():
        return None
    return OpenAI(api_key=key)


def build_lecturer_chat_context(db: Session, user: User, course_id: Optional[str]) -> str:
    if not course_id:
        return ""
    course = db.get(Course, course_id)
    if not course:
        return ""
    try:
        assert_lecturer_owns_course(db, user, course)
    except PermissionError:
        return ""
    students = list_course_students(db, course_id)[:10]
    lines = [
        f"- {s['name']}: mastery {round(float(s.get('overall_mastery') or 0))}%"
        + (f", quiz avg {s['quiz_average']}%" if s.get("quiz_average") is not None else "")
        for s in students
    ]
    return (
        f"\nCOURSE: {course.course_code} — {course.course_title}\n"
        f"ENROLLED STUDENTS ({len(students)} shown):\n"
        + ("\n".join(lines) if lines else "No enrolled students yet.")
    )


def lecturer_ai_chat(db: Session, user: User, message: str, course_id: Optional[str] = None) -> dict:
    dept = user.department or "your department"
    context_data = build_lecturer_chat_context(db, user, course_id)
    system_prompt = f"""You are an AI teaching assistant for a lecturer at Fountain University,
Osogbo, Nigeria. Department: {dept}.

Help with:
1. Interpreting student performance and suggesting interventions
2. Generating quiz questions from course topics when asked
3. Summarizing module topics
4. Practical pedagogical advice for Nigerian university context

Be concise and actionable.
{context_data}"""

    client = _openai_client()
    if not client:
        return {
            "message": (
                "AI assistant is unavailable (OPENAI_API_KEY not configured). "
                "You can still review student analytics on the Dashboard and Students pages."
            ),
            "context_used": bool(context_data),
        }

    model = os.getenv("OPENAI_FAST_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
        max_tokens=600,
    )
    text = (resp.choices[0].message.content or "").strip()
    return {"message": text or "I could not generate a response.", "context_used": bool(context_data)}
