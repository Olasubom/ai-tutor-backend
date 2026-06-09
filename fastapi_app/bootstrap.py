"""Database initialization and default admin seed."""

from __future__ import annotations

import logging
import os
import subprocess
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
            ["alembic", "upgrade", "head"],
            cwd=str(_ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        logger.exception("alembic_upgrade_failed")


def init_database() -> None:
    db = Database()
    Base.metadata.create_all(bind=db.engine)
    run_migrations()
    _seed_admin(db)
    _seed_defaults(db)


def _seed_admin(db: Database) -> None:
    email = os.getenv("ADMIN_EMAIL", "admin@aitutor.edu").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "admin-secret")
    with db._SessionLocal() as session:
        existing = session.scalar(select(User).where(User.email == email))
        if existing:
            return
        session.add(
            User(
                email=email,
                name="Platform Admin",
                hashed_password=hash_password(password),
                role="admin",
                is_active=True,
                is_verified=True,
            )
        )
        session.commit()
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
