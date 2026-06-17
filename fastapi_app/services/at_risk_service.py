from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.core.context import get_runtime
from fastapi_app.admin.models import Course, Department
from fastapi_app.auth.models import User
from fastapi_app.services.enrollment_service import list_course_students
from fastapi_app.services.memory_files import read_json, read_jsonl


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _severity(mastery_pct: float) -> str:
    if mastery_pct < 20:
        return "high"
    if mastery_pct < 30:
        return "medium"
    return "low"


def list_at_risk(lecturer_id: str, db: Session | None = None) -> List[dict]:
    """At-risk students from enrolled rosters + BKT mastery (same source as Students page)."""
    if db is None:
        from agency.core.tools.database import Database

        with Database()._SessionLocal() as session:  # noqa: SLF001
            return list_at_risk(lecturer_id, session)

    user = db.get(User, lecturer_id)
    if not user or user.role not in ("lecturer", "admin"):
        return []

    dismissed = {
        d.get("learner_id")
        for d in read_json(f"at_risk_dismissed/{lecturer_id}.json", [])
    }

    if not user.department:
        return []

    dept = db.scalars(select(Department).where(Department.name == user.department)).first()
    if not dept:
        return []

    courses = db.scalars(
        select(Course).where(Course.department_id == dept.id, Course.is_active == True)  # noqa: E712
    ).all()

    runtime = get_runtime()
    by_student: dict[str, dict] = {}

    for course in courses:
        for s in list_course_students(db, course.id):
            sid = s["student_id"]
            if sid in dismissed:
                continue
            mastery = float(s.get("overall_mastery") or 0)
            if mastery >= 40:
                continue

            profile = runtime.learner_memory.get_profile(sid)
            topic_mastery = profile.get("topic_mastery", {})
            weak_topics = [
                t for t, st in topic_mastery.items() if float(st.get("p_l", 0)) < 0.4
            ][:3]

            last_active = s.get("last_active")
            if not last_active:
                for e in reversed(read_jsonl(f"events/{sid}.jsonl")):
                    ts = e.get("timestamp")
                    if ts:
                        last_active = str(ts)
                        break
            if not last_active:
                last_active = _now()

            severity = _severity(mastery)
            risk_factors = [f"Mastery {round(mastery)}%"]
            risk_factors.extend(f"Low mastery in {t}" for t in weak_topics[:2])

            row = {
                "learner_id": sid,
                "name": s.get("name", sid),
                "email": s.get("email", ""),
                "department": user.department,
                "level": course.level,
                "mastery": round(mastery),
                "severity": severity,
                "weak_topics": weak_topics,
                "risk_factors": risk_factors,
                "modules_done": int(s.get("modules_completed") or 0),
                "last_active": last_active,
                "suggested_action": (
                    f"Schedule a check-in with {s.get('name', 'this student')} "
                    f"and assign review for {', '.join(weak_topics[:2]) or 'weak topics'}."
                ),
            }
            prev = by_student.get(sid)
            if not prev or mastery < prev["mastery"]:
                by_student[sid] = row

    severity_order = {"high": 0, "medium": 1, "low": 2}
    alerts = sorted(
        by_student.values(),
        key=lambda x: (severity_order.get(x["severity"], 3), x["mastery"]),
    )
    return alerts


def dismiss_alert(lecturer_id: str, learner_id: str) -> None:
    items = read_json(f"at_risk_dismissed/{lecturer_id}.json", [])
    items.append({"learner_id": learner_id, "dismissed_at": _now()})
    from fastapi_app.services.memory_files import write_json

    write_json(f"at_risk_dismissed/{lecturer_id}.json", items)
