"""Lecturer-created assessments with BKT integration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from agency.core.context import get_runtime
from agency.core.services.bkt import BKTParams, apply_events
from fastapi_app.models.lecturer_dashboard import (
    CourseModule,
    LecturerQuiz,
    LecturerQuizAttempt,
    QuizQuestion,
    QuizQuestionOption,
)
from fastapi_app.services.lecturer_course_service import assert_lecturer_owns_course
from fastapi_app.services.quiz_ai_service import generate_mcq_questions
from fastapi_app.auth.models import User
from fastapi_app.admin.models import Course

DEFAULT_BKT = BKTParams(p_l0=0.3, p_t=0.09, p_s=0.1, p_g=0.2)


def _module_course(db: Session, module_id: str) -> tuple[CourseModule, Course]:
    mod = db.get(CourseModule, module_id)
    if not mod:
        raise ValueError("Module not found")
    course = db.get(Course, mod.course_id)
    if not course:
        raise ValueError("Course not found")
    return mod, course


def quiz_dict(q: LecturerQuiz, db: Session, *, include_questions: bool = False) -> dict:
    pending = db.scalar(
        select(func.count())
        .select_from(QuizQuestion)
        .where(
            QuizQuestion.quiz_id == q.id,
            QuizQuestion.ai_generated == True,  # noqa: E712
            QuizQuestion.approved == False,  # noqa: E712
        )
    )
    out = {
        "id": q.id,
        "module_id": q.module_id,
        "title": q.title,
        "description": q.description,
        "bloom_level": q.bloom_level,
        "time_limit_minutes": q.time_limit_minutes,
        "max_attempts": q.max_attempts,
        "is_published": q.is_published,
        "created_at": q.created_at.isoformat(),
        "pending_review_count": int(pending or 0),
    }
    if include_questions:
        out["questions"] = [question_dict(qu, db, reveal_answers=True) for qu in _questions(db, q.id)]
    return out


def question_dict(q: QuizQuestion, db: Session, *, reveal_answers: bool = False) -> dict:
    opts = db.scalars(select(QuizQuestionOption).where(QuizQuestionOption.question_id == q.id)).all()
    options = [
        {
            "id": o.id,
            "text": o.text,
            **({"is_correct": o.is_correct} if reveal_answers else {}),
        }
        for o in opts
    ]
    return {
        "id": q.id,
        "text": q.text,
        "question_type": q.question_type,
        "order": q.question_order,
        "difficulty": q.difficulty,
        "explanation": q.explanation if reveal_answers else None,
        "ai_generated": q.ai_generated,
        "approved": q.approved,
        "options": options,
    }


def _questions(db: Session, quiz_id: str, *, include_unapproved: bool = False) -> List[QuizQuestion]:
    q = select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id)
    if not include_unapproved:
        q = q.where(QuizQuestion.approved == True)  # noqa: E712
    return db.scalars(q.order_by(QuizQuestion.question_order)).all()


def get_quiz_for_lecturer(db: Session, user: User, quiz_id: str) -> dict:
    quiz = db.get(LecturerQuiz, quiz_id)
    if not quiz:
        raise ValueError("Quiz not found")
    _, course = _module_course(db, quiz.module_id)
    assert_lecturer_owns_course(db, user, course)
    out = quiz_dict(quiz, db)
    out["questions"] = [
        question_dict(qu, db, reveal_answers=True) for qu in _questions(db, quiz_id, include_unapproved=True)
    ]
    pending = sum(1 for qu in out["questions"] if qu.get("ai_generated") and not qu.get("approved"))
    out["pending_review_count"] = pending
    return out


def create_quiz(db: Session, user: User, module_id: str, data: dict) -> LecturerQuiz:
    _, course = _module_course(db, module_id)
    assert_lecturer_owns_course(db, user, course)
    quiz = LecturerQuiz(
        module_id=module_id,
        title=data["title"],
        description=data.get("description"),
        bloom_level=data.get("bloom_level"),
        time_limit_minutes=data.get("time_limit_minutes"),
        max_attempts=int(data.get("max_attempts", 3)),
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def add_question(db: Session, user: User, quiz_id: str, data: dict) -> QuizQuestion:
    quiz = db.get(LecturerQuiz, quiz_id)
    if not quiz:
        raise ValueError("Quiz not found")
    _, course = _module_course(db, quiz.module_id)
    assert_lecturer_owns_course(db, user, course)
    order = int(
        data.get("order")
        or (db.scalar(select(func.max(QuizQuestion.question_order)).where(QuizQuestion.quiz_id == quiz_id)) or 0)
        + 1
    )
    q = QuizQuestion(
        quiz_id=quiz_id,
        text=data["text"],
        question_type=data.get("question_type", "mcq"),
        question_order=order,
        difficulty=data.get("difficulty", "medium"),
        explanation=data.get("explanation"),
        ai_generated=bool(data.get("ai_generated", False)),
        approved=bool(data.get("approved", True)),
    )
    db.add(q)
    db.flush()
    for opt in data.get("options", []):
        db.add(
            QuizQuestionOption(
                question_id=q.id,
                text=opt["text"],
                is_correct=bool(opt.get("is_correct", False)),
            )
        )
    db.commit()
    db.refresh(q)
    return q


def generate_ai_questions(db: Session, user: User, quiz_id: str, body: dict) -> List[QuizQuestion]:
    quiz = db.get(LecturerQuiz, quiz_id)
    if not quiz:
        raise ValueError("Quiz not found")
    _, course = _module_course(db, quiz.module_id)
    assert_lecturer_owns_course(db, user, course)
    generated = generate_mcq_questions(
        topic=body.get("topic") or quiz.title,
        count=int(body.get("count", 5)),
        difficulty=body.get("difficulty", "medium"),
        bloom_level=body.get("bloom_level", quiz.bloom_level or "understand"),
    )
    created: List[QuizQuestion] = []
    for item in generated:
        created.append(
            add_question(
                db,
                user,
                quiz_id,
                {
                    "text": item["text"],
                    "explanation": item.get("explanation"),
                    "options": item.get("options", []),
                    "ai_generated": True,
                    "approved": False,
                },
            )
        )
    return created


def publish_quiz(db: Session, user: User, quiz_id: str, published: bool = True) -> LecturerQuiz:
    quiz = db.get(LecturerQuiz, quiz_id)
    if not quiz:
        raise ValueError("Quiz not found")
    _, course = _module_course(db, quiz.module_id)
    assert_lecturer_owns_course(db, user, course)
    quiz.is_published = published
    db.commit()
    db.refresh(quiz)
    return quiz


def student_quiz_view(db: Session, quiz_id: str) -> dict:
    quiz = db.get(LecturerQuiz, quiz_id)
    if not quiz or not quiz.is_published:
        raise ValueError("Quiz not found")
    questions = _questions(db, quiz_id)
    return {
        **quiz_dict(quiz, db),
        "questions": [question_dict(q, db, reveal_answers=False) for q in questions],
    }


def start_attempt(db: Session, student_id: str, quiz_id: str) -> LecturerQuizAttempt:
    quiz = db.get(LecturerQuiz, quiz_id)
    if not quiz or not quiz.is_published:
        raise ValueError("Quiz not found")
    count = db.scalar(
        select(func.count())
        .select_from(LecturerQuizAttempt)
        .where(LecturerQuizAttempt.quiz_id == quiz_id, LecturerQuizAttempt.student_id == student_id)
    )
    if count and int(count) >= quiz.max_attempts:
        raise ValueError("Maximum attempts reached")
    attempt = LecturerQuizAttempt(quiz_id=quiz_id, student_id=student_id)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def submit_attempt(db: Session, attempt_id: str, student_id: str, answers: Dict[str, str]) -> dict:
    attempt = db.get(LecturerQuizAttempt, attempt_id)
    if not attempt or attempt.student_id != student_id:
        raise ValueError("Attempt not found")
    if attempt.completed_at:
        raise ValueError("Attempt already submitted")

    quiz = db.get(LecturerQuiz, attempt.quiz_id)
    mod = db.get(CourseModule, quiz.module_id) if quiz else None
    topic = mod.title if mod else quiz.title if quiz else "General"

    questions = _questions(db, attempt.quiz_id)
    results = []
    events = []
    correct = 0
    for q in questions:
        chosen = answers.get(q.id)
        opts = db.scalars(select(QuizQuestionOption).where(QuizQuestionOption.question_id == q.id)).all()
        correct_opt = next((o for o in opts if o.is_correct), None)
        is_correct = bool(correct_opt and chosen == correct_opt.id)
        if is_correct:
            correct += 1
        events.append({"topic": topic, "correct": is_correct, "metadata": {}})
        results.append(
            {
                "question_id": q.id,
                "question_text": q.text,
                "is_correct": is_correct,
                "explanation": q.explanation,
                "correct_option_id": correct_opt.id if correct_opt else None,
            }
        )

    total = len(questions)
    score = round((correct / total) * 100, 1) if total else 0.0
    attempt.score = score
    attempt.correct_count = correct
    attempt.total_questions = total
    attempt.answers = answers
    attempt.completed_at = datetime.now(timezone.utc)
    db.commit()

    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(student_id)
    topic_mastery = profile.get("topic_mastery", {})
    topic_mastery, summary = apply_events(topic_mastery, events)
    weak_quiz_topics = list(profile.get("weak_quiz_topics") or [])
    if score < 60 and topic not in weak_quiz_topics:
        weak_quiz_topics.append(topic)
    runtime.learner_memory.upsert_profile(
        student_id,
        {"topic_mastery": topic_mastery, "knowledge_state_summary": summary, "weak_quiz_topics": weak_quiz_topics},
    )

    return {
        "attempt_id": attempt.id,
        "quiz_id": attempt.quiz_id,
        "score": score,
        "correct_count": correct,
        "total_questions": total,
        "results": results,
    }


def get_ai_quiz_summary(db: Session, course_id: str) -> List[dict]:
    """Aggregate AI/module quiz scores from legacy events and lecturer quiz attempts."""
    from agency.core.tools.models import ContentItem
    from fastapi_app.models.lecturer_dashboard import CourseEnrollment
    from fastapi_app.services.memory_files import read_jsonl

    items = db.scalars(
        select(ContentItem).where(
            ContentItem.course_id == course_id,
            ContentItem.status == "approved",
        )
    ).all()
    student_ids = [
        r
        for r in db.scalars(
            select(CourseEnrollment.student_id).where(
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.status == "active",
            )
        ).all()
    ]

    summaries: List[dict] = []
    for item in items:
        topic = str(item.title or item.topic or "").strip()
        if not topic:
            continue
        scores: List[float] = []
        topic_lower = topic.lower()
        for sid in student_ids:
            for e in read_jsonl(f"events/{sid}.jsonl"):
                if e.get("event_type") != "quiz_submit" and "quiz_id" not in e:
                    continue
                evt_topic = str(e.get("topic") or "").lower()
                if evt_topic == topic_lower or topic_lower in evt_topic or evt_topic in topic_lower:
                    pct = e.get("percentage")
                    if pct is not None:
                        scores.append(float(pct))
        if not scores:
            continue
        summaries.append(
            {
                "topic": topic,
                "type": "ai_generated",
                "attempts": len(scores),
                "avg_score": round(sum(scores) / len(scores), 1),
                "pass_rate": round(sum(1 for s in scores if s >= 60) / len(scores) * 100),
            }
        )

    module_ids = db.scalars(select(CourseModule.id).where(CourseModule.course_id == course_id)).all()
    if module_ids:
        quiz_ids = db.scalars(select(LecturerQuiz.id).where(LecturerQuiz.module_id.in_(module_ids))).all()
        if quiz_ids:
            attempt_scores = db.scalars(
                select(LecturerQuizAttempt.score).where(
                    LecturerQuizAttempt.quiz_id.in_(quiz_ids),
                    LecturerQuizAttempt.score.isnot(None),
                )
            ).all()
            if attempt_scores:
                scores = [float(s) for s in attempt_scores]
                summaries.append(
                    {
                        "topic": "Published module quizzes",
                        "type": "lecturer_quiz",
                        "attempts": len(scores),
                        "avg_score": round(sum(scores) / len(scores), 1),
                        "pass_rate": round(sum(1 for s in scores if s >= 60) / len(scores) * 100),
                    }
                )
    return summaries
