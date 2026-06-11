"""Password reset for DB-backed admin accounts (email verification code via SMTP)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.auth.models import User
from fastapi_app.auth.utils import hash_password
from fastapi_app.services.email_service import is_smtp_configured, send_admin_password_reset_email
from fastapi_app.services.memory_files import read_json, write_json

ADMIN_RESET_CODES_PATH = "auth/admin_reset_codes.json"
RESET_CODE_TTL_MINUTES = 10


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _load_codes() -> dict:
    return read_json(ADMIN_RESET_CODES_PATH, {})


def _save_codes(codes: dict) -> None:
    write_json(ADMIN_RESET_CODES_PATH, codes)


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return email
    if len(local) <= 1:
        masked_local = "*"
    else:
        masked_local = f"{local[0]}{'*' * min(len(local) - 1, 6)}"
    return f"{masked_local}@{domain}"


def request_admin_password_reset(email: str, db: Session) -> dict:
    normalized = _normalize_email(email)
    user = db.scalar(select(User).where(User.email == normalized))
    if not user or user.role != "admin":
        raise HTTPException(status_code=404, detail="No admin account found for this email.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled.")

    if not is_smtp_configured():
        raise HTTPException(
            status_code=503,
            detail="Email is not configured on the server. Set SMTP_USER and SMTP_PASSWORD in agency/.env.",
        )

    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_CODE_TTL_MINUTES)
    codes = _load_codes()
    codes[normalized] = {"code": code, "expires_at": expires_at.isoformat()}
    _save_codes(codes)

    try:
        sent = send_admin_password_reset_email(to_email=normalized, code=code, name=user.name)
    except Exception as exc:
        codes.pop(normalized, None)
        _save_codes(codes)
        raise HTTPException(
            status_code=503,
            detail=f"Could not send verification email. Check SMTP settings. ({exc})",
        ) from exc

    if not sent:
        codes.pop(normalized, None)
        _save_codes(codes)
        raise HTTPException(status_code=503, detail="Could not send verification email. Check SMTP settings.")

    return {
        "message": "Verification code sent to your registered admin email.",
        "email_sent": True,
        "masked_email": _mask_email(normalized),
    }


def verify_admin_reset_code(email: str, code: str) -> None:
    """Validate code without consuming it (allows a separate password step)."""
    normalized = _normalize_email(email)
    record = _load_codes().get(normalized)
    if not record:
        raise HTTPException(status_code=400, detail="Request a new verification code first.")

    expires_at = datetime.fromisoformat(record["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        codes = _load_codes()
        codes.pop(normalized, None)
        _save_codes(codes)
        raise HTTPException(status_code=400, detail="Verification code expired. Request a new one.")

    if record.get("code") != code.strip():
        raise HTTPException(status_code=400, detail="Invalid verification code.")


def reset_admin_password_with_code(*, email: str, code: str, new_password: str, db: Session) -> dict:
    normalized = _normalize_email(email)
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    verify_admin_reset_code(normalized, code)

    user = db.scalar(select(User).where(User.email == normalized))
    if not user or user.role != "admin":
        raise HTTPException(status_code=404, detail="No admin account found for this email.")

    user.hashed_password = hash_password(new_password)
    db.commit()

    codes = _load_codes()
    codes.pop(normalized, None)
    _save_codes(codes)

    return {"ok": True, "message": "Admin password updated successfully."}
