from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from openai import OpenAI

from agency.core.context import get_runtime
from agency.core.services.bkt import BKTParams, apply_events, update_bkt
from agency.tutor_service import handle_recommend_request
from fastapi_app.services import notifications_service
from fastapi_app.services.engagement_service import record_engagement
from fastapi_app.services.memory_files import append_jsonl, read_json, read_jsonl, write_json

DEFAULT_BKT = BKTParams(p_l0=0.3, p_t=0.09, p_s=0.1, p_g=0.2)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _openai_client() -> Optional[OpenAI]:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or "your_key" in key.lower():
        return None
    return OpenAI(api_key=key)


def _fallback_questions(topic: str, n: int, mastery: float) -> List[dict]:
    difficulty = "easy" if mastery < 0.4 else "medium" if mastery < 0.7 else "hard"
    questions = []
    for i in range(n):
        questions.append(
            {
                "question_id": f"q_{i + 1}",
                "question_text": f"({difficulty.title()}) Sample question {i + 1} about {topic}?",
                "options": [
                    f"Option A for {topic}",
                    f"Option B for {topic}",
                    f"Option C for {topic}",
                    f"Option D for {topic}",
                ],
                "difficulty": difficulty,
                "correct_option": i % 4,
            }
        )
    return questions


def generate_quiz(learner_id: str, topic: str, num_questions: int = 5) -> dict:
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    mastery = float(profile.get("topic_mastery", {}).get(topic, {}).get("p_l", 0.3))
    quiz_id = str(uuid.uuid4())
    client = _openai_client()
    questions: List[dict] = []

    if client:
        prompt = (
            f"Generate {num_questions} multiple-choice quiz questions on topic '{topic}' "
            f"for a learner at {int(mastery * 100)}% mastery. "
            "Return JSON: {\"questions\":[{\"question_text\":str,\"options\":[4 strings],"
            "\"difficulty\":\"easy|medium|hard\",\"correct_option\":0-3}]}"
        )
        try:
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[
                    {"role": "system", "content": "You are an academic quiz generator. Return valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            )
            text = resp.choices[0].message.content or "{}"
            payload = json.loads(text.strip().strip("`").replace("json\n", ""))
            for i, q in enumerate(payload.get("questions", [])[:num_questions]):
                questions.append(
                    {
                        "question_id": f"q_{i + 1}",
                        "question_text": q.get("question_text", f"Question {i + 1}"),
                        "options": q.get("options", ["A", "B", "C", "D"])[:4],
                        "difficulty": q.get("difficulty", "medium"),
                        "correct_option": int(q.get("correct_option", 0)),
                    }
                )
        except Exception:
            questions = []

    if not questions:
        questions = _fallback_questions(topic, num_questions, mastery)

    store = {
        "quiz_id": quiz_id,
        "learner_id": learner_id,
        "topic": topic,
        "created_at": _now(),
        "questions": questions,
    }
    write_json(f"quizzes/{learner_id}/{quiz_id}.json", store)
    record_engagement(learner_id, "quiz_start", {"topic": topic, "questions": num_questions})

    public_questions = [
        {
            "question_id": q["question_id"],
            "question_text": q["question_text"],
            "options": q["options"],
            "difficulty": q["difficulty"],
        }
        for q in questions
    ]
    return {"quiz_id": quiz_id, "topic": topic, "questions": public_questions}


def submit_quiz(
    learner_id: str,
    quiz_id: str,
    responses: List[dict],
    *,
    content_item_id: Optional[str] = None,
) -> dict:
    quiz = read_json(f"quizzes/{learner_id}/{quiz_id}.json", None)
    if not quiz:
        raise ValueError("Quiz not found")

    topic = quiz.get("topic", "General")
    qmap = {q["question_id"]: q for q in quiz.get("questions", [])}
    results = []
    events = []
    total_time = 0

    for r in responses:
        qid = r.get("question_id")
        q = qmap.get(qid)
        if not q:
            continue
        selected = int(r.get("selected_option", -1))
        correct_opt = int(q.get("correct_option", 0))
        is_correct = selected == correct_opt
        time_taken = int(r.get("time_taken_seconds", 0))
        total_time += time_taken
        events.append({"topic": topic, "correct": is_correct, "metadata": {"time_taken": time_taken}})
        results.append(
            {
                "question_id": qid,
                "question_text": q.get("question_text"),
                "selected_option": selected,
                "correct_option": correct_opt,
                "is_correct": is_correct,
                "explanation": (
                    f"{'Correct' if is_correct else 'Incorrect'} — review core concepts in {topic}."
                ),
            }
        )

    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    topic_mastery = profile.get("topic_mastery", {})
    prev_state = topic_mastery.get(topic) or {
        "p_l0": DEFAULT_BKT.p_l0,
        "p_t": DEFAULT_BKT.p_t,
        "p_s": DEFAULT_BKT.p_s,
        "p_g": DEFAULT_BKT.p_g,
        "p_l": DEFAULT_BKT.p_l0,
    }
    previous_mastery = float(prev_state.get("p_l", DEFAULT_BKT.p_l0))

    topic_mastery, summary = apply_events(topic_mastery, events)
    new_mastery = float(topic_mastery.get(topic, {}).get("p_l", previous_mastery))
    runtime.learner_memory.upsert_profile(
        learner_id,
        {"topic_mastery": topic_mastery, "knowledge_state_summary": summary},
    )

    score = sum(1 for r in results if r["is_correct"])
    total = len(results)
    percentage = round((score / total) * 100, 1) if total else 0.0

    append_jsonl(
        f"events/{learner_id}.jsonl",
        {
            "timestamp": _now(),
            "event_type": "quiz_submit",
            "quiz_id": quiz_id,
            "topic": topic,
            "score": score,
            "total": total,
            "percentage": percentage,
            "avg_time_per_q": total_time / max(total, 1),
            "mastery_after": new_mastery,
        },
    )
    record_engagement(learner_id, "quiz_submit", {"topic": topic, "questions": total, "score": score})

    if content_item_id:
        try:
            from agency.core.tools.database import Database
            from fastapi_app.services.module_progress_service import upsert_module_progress

            db = Database()
            with db._SessionLocal() as session:  # noqa: SLF001
                upsert_module_progress(
                    session,
                    learner_id=learner_id,
                    content_item_id=content_item_id,
                    percent_complete=100,
                    status="completed",
                )
        except Exception:
            pass

    recommendation_triggered = False
    try:
        handle_recommend_request(learner_id=learner_id, message=f"quiz completed on {topic}", events=events, limit=6)
        recommendation_triggered = True
        notifications_service.create_notification(
            learner_id,
            type="new_resource",
            title="New resources ready",
            body=f"Recommendations updated after your {topic} quiz.",
            action_url="/student/library",
        )
    except Exception:
        pass

    if new_mastery < 0.5 and new_mastery < previous_mastery:
        notifications_service.create_notification(
            learner_id,
            type="mastery_drop",
            title=f"Mastery dropped in {topic}",
            body=f"Your mastery in {topic} is now {int(new_mastery * 100)}%. Consider a review quiz.",
            action_url=f"/student/quiz/{topic}",
        )

    _update_spaced_rep(learner_id, topic, percentage, new_mastery)

    state = topic_mastery.get(topic, prev_state)
    return {
        "quiz_id": quiz_id,
        "topic": topic,
        "score": score,
        "total": total,
        "percentage": percentage,
        "time_taken_seconds": total_time,
        "results": results,
        "mastery_update": {
            "topic": topic,
            "previous_mastery": round(previous_mastery, 4),
            "new_mastery": round(new_mastery, 4),
            "bkt_params": {
                "p_l0": float(state.get("p_l0", DEFAULT_BKT.p_l0)),
                "p_t": float(state.get("p_t", DEFAULT_BKT.p_t)),
                "p_s": float(state.get("p_s", DEFAULT_BKT.p_s)),
                "p_g": float(state.get("p_g", DEFAULT_BKT.p_g)),
            },
        },
        "recommendation_triggered": recommendation_triggered,
    }


def _update_spaced_rep(learner_id: str, topic: str, percentage: float, mastery: float) -> None:
    data = read_json(f"spaced_rep/{learner_id}.json", {})
    entry = data.get(topic, {"interval_days": 1})
    if percentage >= 60:
        entry["interval_days"] = min(int(entry.get("interval_days", 1)) * 2, 30)
    else:
        entry["interval_days"] = 1
    entry["last_quiz_at"] = _now()
    entry["last_mastery"] = mastery
    due = datetime.now(timezone.utc) + timedelta(days=int(entry["interval_days"]))
    entry["due_date"] = due.date().isoformat()
    data[topic] = entry
    write_json(f"spaced_rep/{learner_id}.json", data)


def quiz_history(learner_id: str) -> List[dict]:
    events = read_jsonl(f"events/{learner_id}.jsonl")
    history = []
    for e in reversed(events):
        if e.get("event_type") != "quiz_submit" and "quiz_id" not in e:
            if e.get("quiz_id"):
                pass
            else:
                continue
        if not e.get("quiz_id"):
            continue
        history.append(
            {
                "quiz_id": e.get("quiz_id"),
                "topic": e.get("topic"),
                "score": e.get("score"),
                "percentage": e.get("percentage"),
                "timestamp": e.get("timestamp"),
                "mastery_after": e.get("mastery_after"),
            }
        )
    return history[:50]


def get_bkt_state(learner_id: str, topic: str) -> dict:
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    state = profile.get("topic_mastery", {}).get(topic) or {
        "p_l0": DEFAULT_BKT.p_l0,
        "p_t": DEFAULT_BKT.p_t,
        "p_s": DEFAULT_BKT.p_s,
        "p_g": DEFAULT_BKT.p_g,
        "p_l": DEFAULT_BKT.p_l0,
        "attempts": 0,
        "correct_count": 0,
    }
    summary = profile.get("knowledge_state_summary", {})
    return {
        "topic": topic,
        "mastery_probability": float(state.get("p_l", DEFAULT_BKT.p_l0)),
        "p_l0": float(state.get("p_l0", DEFAULT_BKT.p_l0)),
        "p_t": float(state.get("p_t", DEFAULT_BKT.p_t)),
        "p_s": float(state.get("p_s", DEFAULT_BKT.p_s)),
        "p_g": float(state.get("p_g", DEFAULT_BKT.p_g)),
        "total_attempts": int(state.get("attempts", 0)),
        "correct_attempts": int(state.get("correct_count", 0)),
        "last_updated": profile.get("updated_at", _now()),
        "trend": summary.get("trend", "stable"),
    }


def review_due(learner_id: str) -> List[dict]:
    data = read_json(f"spaced_rep/{learner_id}.json", {})
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    today = datetime.now(timezone.utc).date()
    due_list = []
    for topic, entry in data.items():
        due_str = entry.get("due_date")
        if not due_str:
            continue
        try:
            due_date = datetime.fromisoformat(due_str).date()
        except ValueError:
            continue
        if due_date > today:
            continue
        mastery = float(profile.get("topic_mastery", {}).get(topic, {}).get("p_l", 0.5))
        days_overdue = (today - due_date).days
        due_list.append(
            {
                "topic": topic,
                "due_date": due_str,
                "days_overdue": days_overdue,
                "current_mastery": round(mastery, 4),
                "suggested_question_count": 5,
            }
        )
    return due_list
