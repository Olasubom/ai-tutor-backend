"""Formal grade computation (Nigerian university scale)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.models.lecturer_dashboard import Grade


def compute_grade(total_score: float) -> Tuple[str, float, str]:
    """Return (grade_letter, grade_point, remark) for a total score out of 100."""
    score = max(0.0, min(100.0, float(total_score)))
    if score >= 70:
        return "A", 5.0, "Distinction"
    if score >= 60:
        return "B", 4.0, "Credit"
    if score >= 50:
        return "C", 3.0, "Merit"
    if score >= 45:
        return "D", 2.0, "Pass"
    if score >= 40:
        return "E", 1.0, "Pass"
    return "F", 0.0, "Fail"


def upsert_grade(
    db: Session,
    *,
    student_id: str,
    course_id: str,
    lecturer_id: str,
    ca_score: Optional[float],
    exam_score: Optional[float],
    comment: Optional[str] = None,
    ca_max: float = 40.0,
) -> Grade:
    if ca_score is not None and (ca_score < 0 or ca_score > ca_max):
        raise ValueError(f"ca_score must be between 0 and {ca_max}")
    if exam_score is not None and (exam_score < 0 or exam_score > 60):
        raise ValueError("exam_score must be between 0 and 60")

    total = (ca_score or 0.0) + (exam_score or 0.0)
    letter, point, remark = compute_grade(total)

    row = db.scalars(
        select(Grade).where(Grade.student_id == student_id, Grade.course_id == course_id)
    ).first()
    if row is None:
        row = Grade(student_id=student_id, course_id=course_id, lecturer_id=lecturer_id)
        db.add(row)

    row.lecturer_id = lecturer_id
    row.ca_score = ca_score
    row.exam_score = exam_score
    row.total_score = total
    row.grade_letter = letter
    row.grade_point = point
    row.remark = remark
    row.comment = comment
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def grade_to_dict(
    g: Grade,
    student_name: str = "",
    student_email: str = "",
    *,
    quiz_avg: Optional[float] = None,
    quiz_count: Optional[int] = None,
) -> dict:
    row = {
        "id": g.id,
        "student_id": g.student_id,
        "student_name": student_name,
        "student_email": student_email,
        "course_id": g.course_id,
        "ca_score": g.ca_score,
        "exam_score": g.exam_score,
        "total_score": g.total_score,
        "grade_letter": g.grade_letter,
        "grade_point": g.grade_point,
        "remark": g.remark,
        "comment": g.comment,
        "graded_at": g.graded_at.isoformat() if g.graded_at else None,
        "updated_at": g.updated_at.isoformat() if g.updated_at else None,
    }
    if quiz_avg is not None:
        row["quiz_avg"] = quiz_avg
    if quiz_count is not None:
        row["quiz_count"] = quiz_count
    return row


def list_course_grades_for_course(db: Session, course_id: str) -> list[dict]:
    """All enrolled students with formal grades and quiz participation stats."""
    from fastapi_app.services.enrollment_service import list_course_students

    grade_rows = {
        g.student_id: g for g in db.scalars(select(Grade).where(Grade.course_id == course_id)).all()
    }
    out: list[dict] = []
    for student in list_course_students(db, course_id):
        sid = student["student_id"]
        quiz_avg = student.get("quiz_average")
        quiz_count = student.get("quiz_count")
        grade = grade_rows.get(sid)
        if grade:
            out.append(
                grade_to_dict(
                    grade,
                    student_name=student["name"],
                    student_email=student["email"],
                    quiz_avg=quiz_avg,
                    quiz_count=quiz_count,
                )
            )
        else:
            out.append(
                {
                    "id": None,
                    "student_id": sid,
                    "student_name": student["name"],
                    "student_email": student["email"],
                    "course_id": course_id,
                    "ca_score": None,
                    "exam_score": None,
                    "total_score": None,
                    "grade_letter": None,
                    "grade_point": None,
                    "remark": None,
                    "comment": None,
                    "graded_at": None,
                    "updated_at": None,
                    "quiz_avg": quiz_avg,
                    "quiz_count": quiz_count,
                }
            )
    return out


def export_grades_csv(db: Session, course_id: str) -> str:
    import csv
    import io

    from fastapi_app.auth.models import User

    rows = db.scalars(select(Grade).where(Grade.course_id == course_id)).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Student Name", "Email", "CA", "Exam", "Total", "Grade", "Grade Point", "Remark"])
    for g in rows:
        student = db.get(User, g.student_id)
        writer.writerow(
            [
                student.name if student else g.student_id,
                student.email if student else "",
                g.ca_score,
                g.exam_score,
                g.total_score,
                g.grade_letter,
                g.grade_point,
                g.remark,
            ]
        )
    return buffer.getvalue()
