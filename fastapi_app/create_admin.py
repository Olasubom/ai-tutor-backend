"""
Run this script to create or promote an admin account.

Usage: python -m fastapi_app.create_admin

Or with custom credentials:
  ADMIN_EMAIL=me@example.com ADMIN_PASSWORD=secret python -m fastapi_app.create_admin
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
from sqlalchemy import select

load_dotenv(_ROOT / "agency" / ".env", override=True)

from agency.core.tools.database import Base, Database  # noqa: E402
from fastapi_app.admin.models import AdminNucId, College, Course, Department  # noqa: F401,E402
from fastapi_app.auth.models import User  # noqa: E402
from fastapi_app.auth.utils import hash_password  # noqa: E402
from fastapi_app.bootstrap import init_database  # noqa: E402


def create_admin() -> None:
    init_database()
    db = Database()
    session_factory = db._SessionLocal

    email = os.getenv("ADMIN_EMAIL") or input("Admin email: ").strip()
    password = os.getenv("ADMIN_PASSWORD") or input("Admin password: ").strip()
    name = input("Admin name [Platform Administrator]: ").strip() or "Platform Administrator"

    if not email or not password:
        print("Email and password are required.")
        sys.exit(1)

    email = email.lower().strip()

    with session_factory() as db_session:
        existing = db_session.scalar(select(User).where(User.email == email))
        if existing:
            existing.role = "admin"
            existing.is_verified = True
            existing.is_active = True
            if not existing.institution:
                existing.institution = "Fountain University"
            db_session.commit()
            print(f"Promoted {email} to admin.")
            return

        user = User(
            email=email,
            name=name,
            hashed_password=hash_password(password),
            role="admin",
            is_active=True,
            is_verified=True,
            institution="Fountain University",
        )
        db_session.add(user)
        db_session.commit()
        print(f"Admin created: {email}")


if __name__ == "__main__":
    create_admin()
