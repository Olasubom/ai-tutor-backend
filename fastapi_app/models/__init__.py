"""Lecturer dashboard SQLAlchemy models (imported for create_all / migrations)."""

from fastapi_app.models.lecturer_dashboard import (  # noqa: F401
    Announcement,
    CourseEnrollment,
    CourseModule,
    Grade,
    LecturerQuiz,
    LecturerQuizAttempt,
    ModuleMaterialLink,
    QuizQuestion,
    QuizQuestionOption,
    UserNotification,
)
