#!/usr/bin/env python3
"""Sync CourseEnrollment rows from existing structured memory course lists."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / "agency" / ".env", override=False)

from sqlalchemy import select

from agency.core.tools.database import Database
from fastapi_app.auth.models import User
from fastapi_app.bootstrap import init_database
from fastapi_app.services.course_service import get_course_ids_for_learner
from fastapi_app.services.enrollment_service import sync_enrollments_for_student


def main() -> None:
    init_database()
    db = Database()
    total = 0
    with db._SessionLocal() as session:  # noqa: SLF001
        students = session.scalars(select(User).where(User.role == "student")).all()
        for student in students:
            ids = get_course_ids_for_learner(student.id, session)
            if ids:
                total += sync_enrollments_for_student(session, student.id, ids)
    print(f"Synced enrollments for {len(students)} students ({total} rows upserted)")


if __name__ == "__main__":
    main()
