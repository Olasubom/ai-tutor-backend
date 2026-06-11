"""Database initialization and default admin seed."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import select

from agency.core.tools.database import Base, Database
from fastapi_app.admin.models import AdminNucId, College, Course, Department  # noqa: F401
from fastapi_app.auth.models import User  # noqa: F401
from fastapi_app.auth.utils import hash_password

logger = logging.getLogger(__name__)
_ROOT = Path(__file__).resolve().parents[1]


def run_migrations() -> None:
    alembic_ini = _ROOT / "alembic.ini"
    if not alembic_ini.exists():
        return
    try:
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(_ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        logger.exception("alembic_upgrade_failed")


def _clean_duplicate_courses(db: Database) -> None:
    """Remove duplicate courses keeping only the first inserted one."""
    flag = _ROOT / "memory" / ".courses_duplicate_cleanup_done"
    if flag.exists():
        return

    with db._SessionLocal() as session:
        courses = session.scalars(select(Course).order_by(Course.id)).all()
        seen: set[tuple[str, str, str]] = set()
        to_delete: list[str] = []

        for course in courses:
            key = (course.course_code, course.department_id, course.level)
            if key in seen:
                to_delete.append(course.id)
            else:
                seen.add(key)

        if to_delete:
            for course_id in to_delete:
                row = session.get(Course, course_id)
                if row:
                    session.delete(row)
            session.commit()
            print(f"[CLEANUP] Removed {len(to_delete)} duplicate courses")
        else:
            print("[CLEANUP] No duplicate courses found")

    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.touch()


def init_database() -> None:
    db = Database()
    Base.metadata.create_all(bind=db.engine)
    _clean_duplicate_courses(db)
    run_migrations()
    _seed_admin(db)
    _seed_defaults(db)


def _seed_admin(db: Database) -> None:
    email = os.getenv("ADMIN_EMAIL", "admin@aitutor.edu.ng").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "Admin@AITutor2024")
    with db._SessionLocal() as session:
        existing = session.scalar(select(User).where(User.role == "admin"))
        if existing:
            print(f"[STARTUP] Admin exists: {existing.email}")
            return

        session.add(
            User(
                email=email,
                name="Platform Administrator",
                hashed_password=hash_password(password),
                role="admin",
                is_active=True,
                is_verified=True,
                institution="Fountain University",
            )
        )
        session.commit()
        print(f"[STARTUP] Admin account created: {email}")
        print(f"[STARTUP] Default password: {password}")
        print("[STARTUP] CHANGE THIS PASSWORD after first login!")
        logger.info("seeded_admin_user", extra={"email": email})


def _seed_defaults(db: Database) -> None:
    with db._SessionLocal() as session:
        if session.scalar(select(College).limit(1)):
            return
        eng = College(name="College of Engineering")
        sci = College(name="College of Science")
        session.add_all([eng, sci])
        session.flush()
        csc = Department(name="Computer Science", college_id=eng.id)
        mat = Department(name="Mathematics", college_id=sci.id)
        session.add_all([csc, mat])
        session.flush()
        session.add(
            AdminNucId(
                nuc_staff_id="NUC-2024-001",
                label="Demo Lecturer ID",
                college=eng.name,
                department=csc.name,
                status="active",
            )
        )
        session.add(
            AdminNucId(
                nuc_staff_id="NUC-2024-002",
                label="Demo Lecturer ID (Science)",
                college=sci.name,
                department=mat.name,
                status="active",
            )
        )
        session.commit()
