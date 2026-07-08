from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / "agency" / ".env", override=False)
load_dotenv(_ROOT / ".env", override=False)

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text

from agency.core.tools.database import Base, Database
from agency.core.tools.models import ContentItem, ModuleProgress, ModuleSession  # noqa: F401
from fastapi_app.admin.models import AdminNucId, College, Course, Department  # noqa: F401
from fastapi_app.models import (  # noqa: F401
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
from fastapi_app.auth.models import User  # noqa: F401
from fastapi_app.auth.utils import hash_password

logger = logging.getLogger(__name__)


def _alembic_config() -> Config:
    return Config(str(_ROOT / "alembic.ini"))


def stamp_if_needed(db: Database) -> None:
    """
    If this DB has no alembic_version table yet, it was built directly
    by create_all() + the guarded ALTER TABLE checks, not by Alembic.
    Stamp it at head instead of letting Alembic try to replay DDL that
    already exists, which fails silently. This does not execute any
    schema-changing DDL — it only records migration state.
    """
    inspector = inspect(db.engine)
    if "alembic_version" not in inspector.get_table_names():
        cfg = _alembic_config()
        db_url = str(db.engine.url.render_as_string(hide_password=False))
        cfg.set_main_option("sqlalchemy.url", db_url)
        import dotenv

        _original_load_dotenv = dotenv.load_dotenv

        def _preserve_database_url(*args, **kwargs):
            kwargs["override"] = False
            return _original_load_dotenv(*args, **kwargs)

        dotenv.load_dotenv = _preserve_database_url
        try:
            command.stamp(cfg, "head")
        finally:
            dotenv.load_dotenv = _original_load_dotenv


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


def _migrate_content_items(db: Database) -> None:
    """Add course_id, module_order, status, uploaded_by to existing content_items."""
    inspector = inspect(db.engine)
    if "content_items" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("content_items")}
    dialect = db.engine.dialect.name
    alters: list[str] = []
    if "course_id" not in columns:
        alters.append("ADD COLUMN course_id VARCHAR(36)")
    if "module_order" not in columns:
        alters.append("ADD COLUMN module_order INTEGER")
    if "status" not in columns:
        alters.append("ADD COLUMN status VARCHAR(32) DEFAULT 'approved'")
    if "uploaded_by" not in columns:
        alters.append("ADD COLUMN uploaded_by VARCHAR(36)")
    if "extracted_text" not in columns:
        alters.append("ADD COLUMN extracted_text TEXT")
    if "embedding_status" not in columns:
        alters.append("ADD COLUMN embedding_status VARCHAR(32) DEFAULT 'pending'")
    if "topics_json" not in columns:
        alters.append("ADD COLUMN topics_json TEXT")
    if not alters:
        return
    with db.engine.begin() as conn:
        for clause in alters:
            if dialect == "postgresql":
                conn.execute(text(f"ALTER TABLE content_items {clause}"))
            else:
                conn.execute(text(f"ALTER TABLE content_items {clause}"))


def _migrate_courses(db: Database) -> None:
    """Add lecturer_id and is_active to existing courses table."""
    inspector = inspect(db.engine)
    if "courses" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("courses")}
    alters: list[str] = []
    if "lecturer_id" not in columns:
        alters.append("ADD COLUMN lecturer_id VARCHAR(36)")
    if "is_active" not in columns:
        alters.append("ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
    if not alters:
        return
    with db.engine.begin() as conn:
        for clause in alters:
            conn.execute(text(f"ALTER TABLE courses {clause}"))


def queue_missing_embeddings() -> None:
    """
    Called at startup. Finds approved ContentItems that have extracted_text
    but no local FAISS index (e.g., after a Render deployment wipes the disk).
    Rebuilds indexes in a background thread without blocking app startup.
    """
    import threading

    from fastapi_app.database import SessionLocal
    from fastapi_app.services.module_embedding_service import (
        _faiss_index_path,
        _rebuild_faiss_from_text,
    )

    def _run() -> None:
        db = SessionLocal()
        try:
            items = db.scalars(
                select(ContentItem).where(
                    ContentItem.status == "approved",
                    ContentItem.extracted_text.isnot(None),
                    ContentItem.embedding_status == "embedded",
                )
            ).all()
            queued = 0
            for item in items:
                if _faiss_index_path(item.item_id).exists():
                    continue
                if not item.extracted_text:
                    continue
                try:
                    _rebuild_faiss_from_text(item.item_id, item.extracted_text)
                    queued += 1
                except Exception as exc:
                    print(f"[STARTUP REBUILD] {item.item_id}: {exc}")
            if queued:
                print(f"[STARTUP] Rebuilt FAISS for {queued} module(s) after deployment.")
        finally:
            db.close()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def init_database() -> None:
    db = Database()
    Base.metadata.create_all(bind=db.engine)
    _migrate_content_items(db)
    _migrate_courses(db)
    _clean_duplicate_courses(db)
    stamp_if_needed(db)
    run_migrations()
    _seed_admin(db)
    _seed_defaults(db)
    queue_missing_embeddings()


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
