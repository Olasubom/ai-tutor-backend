"""Student course enrollment (DB + structured memory sync)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from agency.core.context import get_runtime
from agency.core.tools.models import ModuleProgress
from fastapi_app.admin.models import Course
from fastapi_app.auth.memory import get_structured_memory, update_structured_memory
from fastapi_app.auth.models import User
from fastapi_app.models.lecturer_dashboard import CourseEnrollment, LecturerQuizAttempt
from fastapi_app.services.course_service import get_course_ids_for_learner
from fastapi_app.services.memory_files import read_jsonl


def _last_active(student_id: str) -> str | None:
    events = read_jsonl(f"events/{student_id}.jsonl")
    for e in reversed(events):
        if e.get("timestamp"):
            return str(e["timestamp"])
    return None


def sync_enrollments_for_student(db: Session, student_id: str, course_ids: List[str]) -> int:
    """Upsert CourseEnrollment rows for a list of course IDs (idempotent)."""
    count = 0
    for course_id in course_ids:
        if not course_id:
            continue
        try:
            enroll_student(db, student_id, str(course_id))
            count += 1
        except ValueError as exc:
            if "Already enrolled" not in str(exc):
                raise
    return count


def enroll_student(db: Session, student_id: str, course_id: str) -> CourseEnrollment:
    course = db.get(Course, course_id)
    if not course or not course.is_active:
        raise ValueError("Course not found or inactive")

    existing = db.scalars(
        select(CourseEnrollment).where(
            CourseEnrollment.student_id == student_id,
            CourseEnrollment.course_id == course_id,
        )
    ).first()
    if existing:
        if existing.status == "dropped":
            existing.status = "active"
            existing.enrolled_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing)
        else:
            raise ValueError("Already enrolled")
        row = existing
    else:
        row = CourseEnrollment(student_id=student_id, course_id=course_id, status="active")
        db.add(row)
        db.commit()
        db.refresh(row)

    mem = get_structured_memory(student_id)
    courses = list(mem.get("courses") or [])
    if course_id not in courses:
        courses.append(course_id)
        update_structured_memory(student_id, {"courses": courses})
    return row


def drop_enrollment(db: Session, student_id: str, course_id: str) -> None:
    row = db.scalars(
        select(CourseEnrollment).where(
            CourseEnrollment.student_id == student_id,
            CourseEnrollment.course_id == course_id,
        )
    ).first()
    if not row:
        raise ValueError("Not enrolled")
    row.status = "dropped"
    db.commit()

    mem = get_structured_memory(student_id)
    courses = [c for c in (mem.get("courses") or []) if c != course_id]
    update_structured_memory(student_id, {"courses": courses})


def list_student_enrollments(db: Session, student_id: str) -> List[dict]:
    ids = get_course_ids_for_learner(student_id)
    if not ids:
        return []
    courses = db.scalars(select(Course).where(Course.id.in_(ids), Course.is_active == True)).all()  # noqa: E712
    return [
        {
            "id": c.id,
            "code": c.course_code,
            "title": c.course_title,
            "level": c.level,
            "semester": c.semester,
        }
        for c in courses
    ]


def _modules_completed(db: Session, student_id: str) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(ModuleProgress)
            .where(ModuleProgress.learner_id == student_id, ModuleProgress.status == "completed")
        )
        or 0
    )


def _quiz_count(db: Session, student_id: str, course_id: str) -> int:
    from fastapi_app.models.lecturer_dashboard import CourseModule, LecturerQuiz

    count = sum(
        1
        for e in read_jsonl(f"events/{student_id}.jsonl")
        if e.get("event_type") == "quiz_submit" or e.get("quiz_id")
    )
    module_ids = db.scalars(select(CourseModule.id).where(CourseModule.course_id == course_id)).all()
    if module_ids:
        quiz_ids = db.scalars(select(LecturerQuiz.id).where(LecturerQuiz.module_id.in_(module_ids))).all()
        if quiz_ids:
            db_count = db.scalar(
                select(func.count())
                .select_from(LecturerQuizAttempt)
                .where(
                    LecturerQuizAttempt.student_id == student_id,
                    LecturerQuizAttempt.quiz_id.in_(quiz_ids),
                    LecturerQuizAttempt.score.isnot(None),
                )
            )
            count += int(db_count or 0)
    return count


def _quiz_average(db: Session, student_id: str, course_id: str) -> Optional[float]:
    from fastapi_app.models.lecturer_dashboard import CourseModule, LecturerQuiz

    scores: List[float] = []
    module_ids = db.scalars(select(CourseModule.id).where(CourseModule.course_id == course_id)).all()
    if module_ids:
        quiz_ids = db.scalars(select(LecturerQuiz.id).where(LecturerQuiz.module_id.in_(module_ids))).all()
        if quiz_ids:
            db_scores = db.scalars(
                select(LecturerQuizAttempt.score).where(
                    LecturerQuizAttempt.student_id == student_id,
                    LecturerQuizAttempt.quiz_id.in_(quiz_ids),
                    LecturerQuizAttempt.score.isnot(None),
                )
            ).all()
            scores.extend(float(s) for s in db_scores)

    for e in read_jsonl(f"events/{student_id}.jsonl"):
        if e.get("event_type") != "quiz_submit" and "quiz_id" not in e:
            continue
        pct = e.get("percentage")
        if pct is not None:
            scores.append(float(pct))

    if not scores:
        return None
    return round(sum(scores) / len(scores), 1)


def list_course_students(db: Session, course_id: str) -> List[dict]:
    rows = db.scalars(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.status == "active",
        )
    ).all()
    runtime = get_runtime()
    out: List[dict] = []
    for en in rows:
        student = db.get(User, en.student_id)
        if not student:
            continue
        profile = runtime.learner_memory.get_profile(en.student_id)
        summary = profile.get("knowledge_state_summary", {})
        overall = float(summary.get("overall_mastery_percentage", 0) or 0)
        if overall == 0 and profile.get("topic_mastery"):
            vals = [float(v.get("p_l", 0)) for v in profile["topic_mastery"].values()]
            overall = round(sum(vals) / len(vals) * 100, 1) if vals else 0.0
        last_active = _last_active(en.student_id)
        out.append(
            {
                "student_id": en.student_id,
                "name": student.name,
                "email": student.email,
                "enrolled_at": en.enrolled_at.isoformat(),
                "overall_mastery": overall,
                "last_active": last_active,
                "modules_completed": _modules_completed(db, en.student_id),
                "quiz_average": _quiz_average(db, en.student_id, course_id),
                "quiz_count": _quiz_count(db, en.student_id, course_id),
            }
        )
    return out


def remove_student_from_course(db: Session, course_id: str, student_id: str) -> None:
    drop_enrollment(db, student_id, course_id)
