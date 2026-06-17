from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from agency.core.tools.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CourseModule(Base):
    __tablename__ = "course_modules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    module_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    bloom_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class ModuleMaterialLink(Base):
    __tablename__ = "module_material_links"
    __table_args__ = (UniqueConstraint("module_id", "upload_id", name="uq_module_upload"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    module_id: Mapped[str] = mapped_column(String(36), ForeignKey("course_modules.id"), nullable=False, index=True)
    upload_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (UniqueConstraint("student_id", "course_id", name="uq_student_course_enrollment"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id"), nullable=False, index=True)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class LecturerQuiz(Base):
    __tablename__ = "lecturer_quizzes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    module_id: Mapped[str] = mapped_column(String(36), ForeignKey("course_modules.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    bloom_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    quiz_id: Mapped[str] = mapped_column(String(36), ForeignKey("lecturer_quizzes.id"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), default="mcq", nullable=False)
    question_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    difficulty: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class QuizQuestionOption(Base):
    __tablename__ = "quiz_question_options"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    question_id: Mapped[str] = mapped_column(String(36), ForeignKey("quiz_questions.id"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class LecturerQuizAttempt(Base):
    __tablename__ = "lecturer_quiz_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    quiz_id: Mapped[str] = mapped_column(String(36), ForeignKey("lecturer_quizzes.id"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    time_taken_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Grade(Base):
    __tablename__ = "grades"
    __table_args__ = (UniqueConstraint("student_id", "course_id", name="uq_student_course_grade"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id"), nullable=False, index=True)
    lecturer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    ca_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    exam_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    grade_letter: Mapped[str | None] = mapped_column(String(8), nullable=True)
    grade_point: Mapped[float | None] = mapped_column(Float, nullable=True)
    remark: Mapped[str | None] = mapped_column(String(64), nullable=True)
    graded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id"), nullable=False, index=True)
    lecturer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class UserNotification(Base):
    __tablename__ = "user_notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    announcement_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("announcements.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(64), default="announcement", nullable=False)
