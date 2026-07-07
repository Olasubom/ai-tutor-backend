#!/usr/bin/env python3
"""Verify Phase 3: MCQ option shuffle and correct_index distribution."""
from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / "agency" / ".env", override=False)

from fastapi_app.services.quiz_ai_service import _shuffle_mcq_options, generate_mixed_quiz


def test_shuffle_preserves_correct_answer() -> None:
    mcq = [
        {
            "id": "q1",
            "question": "Which is correct?",
            "options": ["A. Wrong", "B. Also wrong", "C. Right answer", "D. Nope"],
            "correct_index": 2,
            "explanation": "C is correct",
        }
    ]
    for _ in range(50):
        out = _shuffle_mcq_options(mcq)[0]
        idx = out["correct_index"]
        selected = out["options"][idx]
        assert "Right answer" in selected, (idx, out["options"])
    print("Shuffle sync: correct option text matches correct_index (50 iterations)")


def test_shuffle_spreads_index_zero_bias() -> None:
    """Simulate LLM bias (always index 0) — shuffle should spread indices."""
    mcq = [
        {
            "id": f"q{i}",
            "options": [f"A. opt{i}a", f"B. opt{i}b", f"C. opt{i}c", f"D. opt{i}d"],
            "correct_index": 0,
        }
        for i in range(3)
    ]
    counts: Counter[int] = Counter()
    runs = 200
    for _ in range(runs):
        shuffled = _shuffle_mcq_options(mcq)
        for q in shuffled:
            counts[q["correct_index"]] += 1

    total = sum(counts.values())
    print(f"Shuffle distribution over {runs} runs x 3 MCQ ({total} samples):")
    for i in range(4):
        pct = 100 * counts[i] / total
        print(f"  index {i}: {counts[i]} ({pct:.1f}%)")

    assert counts[0] < total * 0.4, "Still clustered on index 0 after shuffle"
    assert len([c for c in counts.values() if c > 0]) >= 3, "Should use at least 3 indices"
    print("Shuffle distribution: not clustered on index 0")


def test_llm_quizzes(num_runs: int = 10) -> None:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or "your_key" in key.lower():
        print("Skipping LLM distribution test (no API key)")
        return

    subject_ctx = {"department": "Law", "course_title": "Contract Law"}
    content = (
        "An offer is a definite promise to be bound. Acceptance must be communicated. "
        "Consideration is required for contract validity."
    )
    counts: Counter[int] = Counter()
    total_mcq = 0
    for run in range(num_runs):
        quiz = generate_mixed_quiz(subject_ctx=subject_ctx, content=content, num_mcq=3, num_short_answer=2)
        for q in quiz.get("mcq", []):
            idx = q.get("correct_index", -1)
            counts[idx] += 1
            total_mcq += 1
            opt = q.get("options", [])
            if 0 <= idx < len(opt):
                print(f"  run {run + 1}: {q.get('id')} correct_index={idx} -> {opt[idx][:60]}")
            else:
                print(f"  run {run + 1}: invalid correct_index={idx}")

    print(f"LLM+shuffle distribution ({total_mcq} MCQ across {num_runs} quizzes):")
    for i in range(4):
        pct = 100 * counts[i] / total_mcq if total_mcq else 0
        print(f"  index {i}: {counts[i]} ({pct:.1f}%)")
    assert total_mcq > 0, "No MCQ generated"
    assert counts[0] < total_mcq * 0.5, "Still heavily clustered on index 0"


def main() -> None:
    test_shuffle_preserves_correct_answer()
    test_shuffle_spreads_index_zero_bias()
    test_llm_quizzes(10)
    print("PHASE 3 VERIFY: PASS")


if __name__ == "__main__":
    main()
