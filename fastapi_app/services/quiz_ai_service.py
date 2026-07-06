"""OpenAI MCQ generation for lecturer assessments and module mixed quizzes."""

from __future__ import annotations

import json
import os
import re
from typing import List

from openai import OpenAI


def _client() -> OpenAI | None:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or "your_key" in key.lower():
        return None
    return OpenAI(api_key=key)


def _call_llm(prompt: str) -> str:
    client = _client()
    if not client:
        return ""
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages=[
            {"role": "system", "content": "Return valid JSON only when asked. Be concise."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
        max_tokens=1200,
    )
    return (resp.choices[0].message.content or "").strip()


def generate_mcq_questions(
    *,
    topic: str,
    count: int = 5,
    difficulty: str = "medium",
    bloom_level: str = "understand",
) -> List[dict]:
    client = _client()
    if not client:
        return [
            {
                "text": f"Sample {difficulty} question about {topic}?",
                "options": [
                    {"text": "Option A", "is_correct": True},
                    {"text": "Option B", "is_correct": False},
                    {"text": "Option C", "is_correct": False},
                    {"text": "Option D", "is_correct": False},
                ],
                "explanation": f"Review core concepts in {topic}.",
            }
            for _ in range(count)
        ]

    prompt = (
        f"Generate {count} multiple-choice questions on '{topic}' "
        f"at {difficulty} difficulty, Bloom level {bloom_level}. "
        'Return JSON array: [{"text": str, "options": [{"text": str, "is_correct": bool}], "explanation": str}]'
    )
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages=[
            {"role": "system", "content": "Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
    )
    raw = (resp.choices[0].message.content or "[]").strip().strip("`").replace("json\n", "")
    data = json.loads(raw)
    if not isinstance(data, list):
        return []
    return data[:count]


def generate_mixed_quiz(
    subject_ctx: dict,
    content: str,
    num_mcq: int = 3,
    num_short_answer: int = 2,
) -> dict:
    """Generate MCQ + typed short-answer questions for any subject."""
    prompt = f"""You are creating a quiz for a {subject_ctx.get('department', 'General Studies')} student
at Fountain University, Nigeria.

COURSE: {subject_ctx.get('course_title', '')}
CONTENT: {content[:2000]}

Generate {num_mcq} multiple choice questions AND {num_short_answer} short answer
questions based ONLY on the content above.

MULTIPLE CHOICE (generate {num_mcq}):
4 options each, one correct. Nigerian-relevant scenarios where natural for this subject.

SHORT ANSWER (generate {num_short_answer}):
Require the student to TYPE their understanding.

Return ONLY valid JSON, no markdown:
{{
  "mcq": [
    {{"id": "q1", "type": "mcq", "question": "...",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct_index": 0, "explanation": "..."}}
  ],
  "short_answer": [
    {{"id": "sa1", "type": "short_answer", "question": "...",
      "model_answer": "...", "key_points": ["point 1", "point 2", "point 3"]}}
  ]
}}"""

    raw = _call_llm(prompt)
    try:
        clean = re.sub(r"```json|```", "", raw).strip()
        return json.loads(clean)
    except Exception:
        return {"mcq": [], "short_answer": []}


def grade_short_answer(
    question: str,
    model_answer: str,
    key_points: list,
    student_answer: str,
    subject_ctx: dict,
) -> dict:
    """AI grades a typed short answer for any subject."""
    prompt = f"""You are grading a {subject_ctx.get('department', 'General Studies')} answer
at Fountain University, Nigeria.

COURSE: {subject_ctx.get('course_title', '')}
QUESTION: {question}
MODEL ANSWER: {model_answer}
KEY POINTS TO COVER: {', '.join(key_points)}

STUDENT'S ANSWER: "{student_answer}"

Grade this answer — check key points covered, correct terminology used,
penalize factual errors. Do not require exact wording.

Return ONLY this JSON (no markdown):
{{
  "score": 0,
  "points_covered": ["..."],
  "points_missed": ["..."],
  "feedback": "2-3 sentences. Encouraging."
}}"""

    raw = _call_llm(prompt)
    try:
        clean = re.sub(r"```json|```", "", raw).strip()
        result = json.loads(clean)
        result["score"] = int(result.get("score", 50))
        return result
    except Exception:
        return {
            "score": 50,
            "feedback": "Answer recorded.",
            "points_covered": [],
            "points_missed": [],
        }
