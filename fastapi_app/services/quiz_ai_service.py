"""OpenAI MCQ generation for lecturer assessments."""

from __future__ import annotations

import json
import os
from typing import List

from openai import OpenAI


def _client() -> OpenAI | None:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or "your_key" in key.lower():
        return None
    return OpenAI(api_key=key)


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
            for i in range(count)
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
