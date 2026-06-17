"""Lecturer assessment and student quiz-taking routes (DB-backed)."""

from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.auth.models import User
from fastapi_app.auth.utils import require_role
from fastapi_app.database import get_db
from fastapi_app.models.lecturer_dashboard import CourseModule, LecturerQuiz, QuizQuestion
from fastapi_app.schemas.lecturer_dashboard import (
    GenerateQuestionsRequest,
    QuestionCreate,
    QuestionUpdate,
    QuizCreate,
    QuizSubmitAnswersRequest,
    QuizUpdate,
)
from fastapi_app.services import lecturer_quiz_service as svc
from fastapi_app.services import notifications_service

router = APIRouter(tags=["Lecturer Quizzes"])


def _user(db: Session, current: dict) -> User:
    user = db.get(User, current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/lecturer/modules/{module_id}/quizzes")
def create_quiz(
    module_id: str,
    payload: QuizCreate,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    try:
        quiz = svc.create_quiz(db, _user(db, current), module_id, payload.model_dump())
        return svc.quiz_dict(quiz, db)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/lecturer/quizzes/{quiz_id}")
def get_quiz(
    quiz_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    try:
        return svc.get_quiz_for_lecturer(db, _user(db, current), quiz_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/lecturer/modules/{module_id}/quizzes")
def list_quizzes(
    module_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    rows = db.scalars(select(LecturerQuiz).where(LecturerQuiz.module_id == module_id)).all()
    return [svc.quiz_dict(q, db) for q in rows]


@router.put("/lecturer/quizzes/{quiz_id}")
def update_quiz(
    quiz_id: str,
    payload: QuizUpdate,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    quiz = db.get(LecturerQuiz, quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    patch = payload.model_dump(exclude_none=True)
    for key, val in patch.items():
        setattr(quiz, key, val)
    db.commit()
    db.refresh(quiz)
    return svc.quiz_dict(quiz, db)


@router.delete("/lecturer/quizzes/{quiz_id}")
def delete_quiz(
    quiz_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    quiz = db.get(LecturerQuiz, quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    db.delete(quiz)
    db.commit()
    return {"message": "Quiz deleted"}


@router.post("/lecturer/quizzes/{quiz_id}/publish")
def publish_quiz(
    quiz_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    try:
        quiz = svc.publish_quiz(db, _user(db, current), quiz_id, published=True)
        mod = db.get(CourseModule, quiz.module_id)
        if mod:
            notifications_service.notify_enrolled_students(
                db,
                mod.course_id,
                title=f"New quiz: {quiz.title}",
                message="A quiz has been published for your course.",
                notification_type="quiz_published",
            )
        return svc.quiz_dict(quiz, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/lecturer/quizzes/{quiz_id}/unpublish")
def unpublish_quiz(
    quiz_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    quiz = svc.publish_quiz(db, _user(db, current), quiz_id, published=False)
    return svc.quiz_dict(quiz, db)


@router.post("/lecturer/quizzes/{quiz_id}/questions")
def add_question(
    quiz_id: str,
    payload: QuestionCreate,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    try:
        q = svc.add_question(db, _user(db, current), quiz_id, payload.model_dump())
        return svc.question_dict(q, db, reveal_answers=True)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/lecturer/questions/{question_id}")
def update_question(
    question_id: str,
    payload: QuestionUpdate,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    q = db.get(QuizQuestion, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    patch = payload.model_dump(exclude_none=True)
    if "text" in patch:
        q.text = patch["text"]
    if "difficulty" in patch:
        q.difficulty = patch["difficulty"]
    if "explanation" in patch:
        q.explanation = patch["explanation"]
    db.commit()
    return svc.question_dict(q, db, reveal_answers=True)


@router.delete("/lecturer/questions/{question_id}")
def delete_question(
    question_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    q = db.get(QuizQuestion, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(q)
    db.commit()
    return {"message": "Question deleted"}


@router.post("/lecturer/quizzes/{quiz_id}/generate-questions")
def generate_questions(
    quiz_id: str,
    payload: GenerateQuestionsRequest,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    try:
        created = svc.generate_ai_questions(db, _user(db, current), quiz_id, payload.model_dump())
        return [svc.question_dict(q, db, reveal_answers=True) for q in created]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/lecturer/questions/{question_id}/approve")
def approve_question(
    question_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    q = db.get(QuizQuestion, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    q.approved = True
    db.commit()
    return svc.question_dict(q, db, reveal_answers=True)


@router.post("/lecturer/questions/{question_id}/reject")
def reject_question(
    question_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    q = db.get(QuizQuestion, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(q)
    db.commit()
    return {"message": "Question rejected and deleted"}


@router.get("/student/courses/{course_id}/quizzes")
def student_list_quizzes(course_id: str, db: Session = Depends(get_db)):
    module_ids = db.scalars(select(CourseModule.id).where(CourseModule.course_id == course_id)).all()
    if not module_ids:
        return []
    rows = db.scalars(
        select(LecturerQuiz).where(
            LecturerQuiz.module_id.in_(module_ids),
            LecturerQuiz.is_published == True,  # noqa: E712
        )
    ).all()
    return [svc.quiz_dict(q, db) for q in rows]


@router.get("/student/quizzes/{quiz_id}")
def student_get_quiz(
    quiz_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("student"))] = None,
):
    try:
        return svc.student_quiz_view(db, quiz_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/student/quizzes/{quiz_id}/start")
def student_start_quiz(
    quiz_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("student"))] = None,
):
    try:
        attempt = svc.start_attempt(db, current["user_id"], quiz_id)
        return {"attempt_id": attempt.id, "quiz_id": quiz_id}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/student/attempts/{attempt_id}/submit")
def student_submit_attempt(
    attempt_id: str,
    payload: QuizSubmitAnswersRequest,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("student"))] = None,
):
    try:
        return svc.submit_attempt(db, attempt_id, current["user_id"], payload.answers)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/student/attempts/{attempt_id}/results")
def student_attempt_results(
    attempt_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("student"))] = None,
):
    from fastapi_app.models.lecturer_dashboard import LecturerQuizAttempt

    attempt = db.get(LecturerQuizAttempt, attempt_id)
    if not attempt or attempt.student_id != current["user_id"] or not attempt.completed_at:
        raise HTTPException(status_code=404, detail="Results not found")
    return {
        "attempt_id": attempt.id,
        "score": attempt.score,
        "correct_count": attempt.correct_count,
        "total_questions": attempt.total_questions,
        "completed_at": attempt.completed_at.isoformat(),
    }


@router.get("/student/quizzes/{quiz_id}/attempts")
def student_quiz_attempts(
    quiz_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("student"))] = None,
):
    from fastapi_app.models.lecturer_dashboard import LecturerQuizAttempt

    rows = db.scalars(
        select(LecturerQuizAttempt).where(
            LecturerQuizAttempt.quiz_id == quiz_id,
            LecturerQuizAttempt.student_id == current["user_id"],
        )
    ).all()
    return [
        {
            "attempt_id": a.id,
            "score": a.score,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        }
        for a in rows
    ]
