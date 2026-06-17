"""Lecturer analytics over enrolled students and module progress."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from agency.core.context import get_runtime
from agency.core.tools.models import ModuleProgress, TopicMastery
from fastapi_app.admin.models import Course
from fastapi_app.auth.models import User
from fastapi_app.models.lecturer_dashboard import CourseEnrollment, CourseModule, LecturerQuiz, LecturerQuizAttempt
from fastapi_app.services.enrollment_service import _last_active, list_course_students
from fastapi_app.services.memory_files import read_jsonl


def get_course_overview(db: Session, course_id: str) -> dict:
    course = db.get(Course, course_id)
    if not course:
        raise ValueError("Course not found")
    students = list_course_students(db, course_id)
    masteries = [float(s.get("overall_mastery") or 0) for s in students]
    avg_mastery = round(sum(masteries) / len(masteries), 1) if masteries else 0.0
    at_risk = sum(1 for m in masteries if m < 40)

    modules = db.scalars(select(CourseModule).where(CourseModule.course_id == course_id)).all()
    module_stats = []
    for mod in modules:
        quiz_ids = db.scalars(select(LecturerQuiz.id).where(LecturerQuiz.module_id == mod.id)).all()
        scores = []
        if quiz_ids:
            scores = db.scalars(
                select(LecturerQuizAttempt.score).where(
                    LecturerQuizAttempt.quiz_id.in_(quiz_ids),
                    LecturerQuizAttempt.score.isnot(None),
                )
            ).all()
        module_stats.append(
            {
                "module_title": mod.title,
                "completion_rate": 0.0,
                "avg_score": round(sum(float(s) for s in scores) / len(scores), 1) if scores else 0.0,
            }
        )

    runtime = get_runtime()
    student_ids = [s["student_id"] for s in students]
    struggled: List[str] = []
    if student_ids:
        rows = db.scalars(
            select(TopicMastery).where(
                TopicMastery.learner_id.in_(student_ids),
                TopicMastery.attempts >= 2,
                TopicMastery.p_l < 0.4,
            )
        ).all()
        topic_avgs: dict[str, List[float]] = {}
        for row in rows:
            topic_avgs.setdefault(row.topic, []).append(float(row.p_l))
        if not topic_avgs:
            for s in students:
                profile = runtime.learner_memory.get_profile(s["student_id"])
                for topic, state in profile.get("topic_mastery", {}).items():
                    attempts = int(state.get("attempts") or state.get("n") or 0)
                    p_l = float(state.get("p_l", 0))
                    if attempts >= 2 and p_l < 0.4:
                        topic_avgs.setdefault(topic, []).append(p_l)
        struggled = sorted(
            topic_avgs.keys(),
            key=lambda t: sum(topic_avgs[t]) / len(topic_avgs[t]) if topic_avgs[t] else 1.0,
        )[:5]

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    active = 0
    for s in students:
        la = _last_active(s["student_id"])
        if la:
            try:
                if datetime.fromisoformat(la.replace("Z", "+00:00")) >= week_ago:
                    active += 1
            except ValueError:
                pass

    return {
        "course_id": course_id,
        "course_title": course.course_title,
        "total_students": len(students),
        "avg_mastery": avg_mastery,
        "students_at_risk": at_risk,
        "modules_completion_rate": module_stats,
        "most_struggled_topics": struggled,
        "active_this_week": active,
    }


def get_course_students_analytics(db: Session, course_id: str) -> List[dict]:
    students = list_course_students(db, course_id)
    runtime = get_runtime()
    out = []
    for s in students:
        profile = runtime.learner_memory.get_profile(s["student_id"])
        mastery = float(s.get("overall_mastery") or 0)
        status = "on_track"
        if mastery < 40:
            status = "at_risk"
        la = s.get("last_active")
        if la:
            try:
                if datetime.fromisoformat(str(la).replace("Z", "+00:00")) < datetime.now(timezone.utc) - timedelta(days=14):
                    status = "inactive"
            except ValueError:
                pass
        topic_mastery = {
            t: round(float(v.get("p_l", 0)) * 100, 1) for t, v in profile.get("topic_mastery", {}).items()
        }
        out.append(
            {
                **s,
                "status": status,
                "topic_mastery": topic_mastery,
            }
        )
    return out


def get_ai_quiz_summary(db: Session, course_id: str) -> List[dict]:
    """Aggregate AI/module quiz scores from legacy events and lecturer quiz attempts."""
    from agency.core.tools.models import ContentItem

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


def get_module_analytics(db: Session, course_id: str, module_id: str) -> dict:
    mod = db.get(CourseModule, module_id)
    if not mod or mod.course_id != course_id:
        raise ValueError("Module not found")
    enrollments = db.scalars(
        select(CourseEnrollment.student_id).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.status == "active",
        )
    ).all()
    started = 0
    completed = 0
    for sid in enrollments:
        row = db.scalars(
            select(ModuleProgress).where(
                ModuleProgress.learner_id == sid,
            )
        ).first()
        if row:
            started += 1
            if row.status == "completed":
                completed += 1

    quiz_ids = db.scalars(select(LecturerQuiz.id).where(LecturerQuiz.module_id == module_id)).all()
    attempts = db.scalars(
        select(LecturerQuizAttempt).where(
            LecturerQuizAttempt.quiz_id.in_(quiz_ids),
            LecturerQuizAttempt.score.isnot(None),
        )
    ).all() if quiz_ids else []
    scores = [float(a.score) for a in attempts if a.score is not None]
    dist = {"0-39": 0, "40-59": 0, "60-79": 0, "80-100": 0}
    for sc in scores:
        if sc < 40:
            dist["0-39"] += 1
        elif sc < 60:
            dist["40-59"] += 1
        elif sc < 80:
            dist["60-79"] += 1
        else:
            dist["80-100"] += 1

    return {
        "module_id": module_id,
        "module_title": mod.title,
        "students_started": started,
        "students_completed": completed,
        "avg_quiz_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
        "quiz_attempts": len(attempts),
        "score_distribution": dist,
    }
