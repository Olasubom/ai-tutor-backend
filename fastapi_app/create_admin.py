"""
Run this script to create or promote an admin account.

Usage:
  python -m fastapi_app.create_admin

With custom credentials (shell env wins over agency/.env):
  $env:ADMIN_EMAIL="you@gmail.com"
  $env:ADMIN_PASSWORD="YourPassword123"
  python -m fastapi_app.create_admin

Change the existing admin's email (keeps one admin, updates email + password):
  $env:ADMIN_EMAIL="you@gmail.com"
  $env:ADMIN_PASSWORD="YourPassword123"
  $env:ADMIN_REPLACE_EMAIL="true"
  python -m fastapi_app.create_admin
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
from sqlalchemy import select

# Shell env (e.g. PowerShell $env:ADMIN_EMAIL) must win over agency/.env
load_dotenv(_ROOT / "agency" / ".env", override=False)

from agency.core.tools.database import Base, Database  # noqa: E402
from fastapi_app.admin.models import AdminNucId, College, Course, Department  # noqa: F401,E402
from fastapi_app.auth.models import User  # noqa: E402
from fastapi_app.auth.utils import hash_password  # noqa: E402
from fastapi_app.bootstrap import init_database  # noqa: E402


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def replace_admin_email(
    *,
    new_email: str,
    password: str,
    name: str | None = None,
    old_email: str | None = None,
) -> None:
    db = Database()
    new_email = new_email.lower().strip()

    with db._SessionLocal() as session:
        if old_email:
            admin = session.scalar(
                select(User).where(User.email == old_email.lower().strip(), User.role == "admin")
            )
        else:
            admin = session.scalar(
                select(User).where(User.role == "admin").order_by(User.created_at.asc())
            )

        if not admin:
            print("No admin account found to update.")
            sys.exit(1)

        conflict = session.scalar(
            select(User).where(User.email == new_email, User.id != admin.id)
        )
        if conflict:
            print(f"Cannot change email: {new_email} is already used by another account.")
            sys.exit(1)

        previous = admin.email
        admin.email = new_email
        admin.hashed_password = hash_password(password)
        admin.role = "admin"
        admin.is_verified = True
        admin.is_active = True
        if name:
            admin.name = name
        if not admin.institution:
            admin.institution = "Fountain University"
        session.commit()

        print(f"Admin email changed: {previous} -> {new_email}")
        print(f"Admin password updated for {new_email}.")


def create_admin(*, replace_email: bool = False) -> None:
    if replace_email or _truthy(os.getenv("ADMIN_REPLACE_EMAIL")):
        pass
    else:
        init_database()
    db = Database()
    session_factory = db._SessionLocal

    email = os.getenv("ADMIN_EMAIL") or input("Admin email: ").strip()
    password = os.getenv("ADMIN_PASSWORD") or input("Admin password: ").strip()
    name = os.getenv("ADMIN_NAME") or input("Admin name [Platform Administrator]: ").strip()
    name = name or "Platform Administrator"

    if not email or not password:
        print("Email and password are required.")
        sys.exit(1)

    email = email.lower().strip()

    if replace_email or _truthy(os.getenv("ADMIN_REPLACE_EMAIL")):
        replace_admin_email(
            new_email=email,
            password=password,
            name=name,
            old_email=os.getenv("ADMIN_OLD_EMAIL"),
        )
        return

    with session_factory() as db_session:
        existing_admin = db_session.scalar(select(User).where(User.role == "admin"))
        existing = db_session.scalar(select(User).where(User.email == email))

        if existing:
            existing.role = "admin"
            existing.is_verified = True
            existing.is_active = True
            if not existing.institution:
                existing.institution = "Fountain University"
            existing.hashed_password = hash_password(password)
            if name:
                existing.name = name
            db_session.commit()
            print(f"Updated admin account: {email}")
            return

        if existing_admin:
            print(
                f"An admin already exists ({existing_admin.email}). "
                f"To change the admin email to {email}, run:\n"
                f'  $env:ADMIN_EMAIL="{email}"\n'
                f'  $env:ADMIN_PASSWORD="your-password"\n'
                f'  $env:ADMIN_REPLACE_EMAIL="true"\n'
                f"  python -m fastapi_app.create_admin"
            )
            sys.exit(1)

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update the platform admin account.")
    parser.add_argument(
        "--replace-email",
        action="store_true",
        help="Change the existing admin's email to ADMIN_EMAIL (also updates password).",
    )
    args = parser.parse_args()
    create_admin(replace_email=args.replace_email)


if __name__ == "__main__":
    main()
