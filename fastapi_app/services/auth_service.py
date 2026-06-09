"""Credential storage, login, and password-reset codes (file-backed)."""

from __future__ import annotations

import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from fastapi import HTTPException

from fastapi_app.services.email_service import is_smtp_configured, send_password_reset_email
from fastapi_app.services.jwt_service import create_access_token
from fastapi_app.services.memory_files import read_json, write_json

USERS_PATH = "auth/users.json"
RESET_CODES_PATH = "auth/reset_codes.json"
RESET_CODE_TTL_MINUTES = 10

def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_password_bcrypt(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_legacy_pbkdf2(password: str, salt: str, password_hash: str) -> bool:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return secrets.compare_digest(digest.hex(), password_hash)


def _verify_password(password: str, user: Dict[str, Any]) -> bool:
    stored = user.get("password_hash", "")
    scheme = user.get("hash_scheme", "pbkdf2")
    if scheme == "bcrypt" or str(stored).startswith("$2"):
        return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
    salt = user.get("salt", "")
    if salt and stored:
        return _verify_legacy_pbkdf2(password, salt, stored)
    return False


def _load_users() -> Dict[str, Dict[str, Any]]:
    return read_json(USERS_PATH, {})


def _save_users(users: Dict[str, Dict[str, Any]]) -> None:
    write_json(USERS_PATH, users)


def _load_reset_codes() -> Dict[str, Dict[str, Any]]:
    return read_json(RESET_CODES_PATH, {})


def _save_reset_codes(codes: Dict[str, Dict[str, Any]]) -> None:
    write_json(RESET_CODES_PATH, codes)


def _learner_id_for_user(user_id: str, role: str) -> Optional[str]:
    if role == "student":
        return f"learner_{user_id.replace('user_', '')}" if user_id.startswith("user_") else f"learner_{user_id}"
    return None


def _public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    user_id = user.get("user_id", "")
    role = user.get("role", "student")
    return {
        "user_id": user_id,
        "email": user.get("email"),
        "name": user.get("name") or user.get("email", "").split("@")[0],
        "role": role,
        "learner_id": _learner_id_for_user(user_id, role),
        "onboarding_complete": user.get("onboarding_complete", False),
        "status": user.get("status", "active"),
    }


def sync_credentials(*, email: str, password: str, name: Optional[str] = None, role: str = "student") -> dict:
    normalized = _normalize_email(email)
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    users = _load_users()
    existing = users.get(normalized, {})
    user_id = existing.get("user_id") or f"user_{uuid.uuid4().hex[:12]}"
    users[normalized] = {
        "email": normalized,
        "user_id": user_id,
        "name": name or existing.get("name"),
        "role": role or existing.get("role", "student"),
        "hash_scheme": "bcrypt",
        "password_hash": _hash_password_bcrypt(password),
        "status": existing.get("status", "active"),
        "onboarding_complete": existing.get("onboarding_complete", False),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_users(users)
    return {"ok": True}


def login(*, email: str, password: str) -> dict:
    normalized = _normalize_email(email)
    user = _load_users().get(normalized)
    if not user or not _verify_password(password, user):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if user.get("status") not in (None, "active"):
        raise HTTPException(status_code=403, detail="Account is not active.")

    public = _public_user(user)
    token = create_access_token(
        {
            "sub": public["user_id"],
            "email": public["email"],
            "name": public["name"],
            "role": public["role"],
            "learner_id": public.get("learner_id"),
        }
    )
    return {"access_token": token, "token_type": "bearer", "user": public}


def register(*, email: str, password: str, name: str, role: str = "student") -> dict:
    normalized = _normalize_email(email)
    users = _load_users()
    if normalized in users:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    sync_credentials(email=normalized, password=password, name=name, role=role)
    return login(email=normalized, password=password)


def request_password_reset(email: str) -> dict:
    normalized = _normalize_email(email)
    users = _load_users()
    user = users.get(normalized)
    if not user:
        raise HTTPException(status_code=404, detail="No account found with that email address.")
    if user.get("role") == "admin":
        raise HTTPException(
            status_code=400,
            detail="Admin accounts cannot reset password here. Use the admin secret at /admin/login.",
        )

    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_CODE_TTL_MINUTES)
    codes = _load_reset_codes()
    codes[normalized] = {"code": code, "expires_at": expires_at.isoformat()}
    _save_reset_codes(codes)

    email_sent = False
    dev_code: Optional[str] = None

    if is_smtp_configured():
        try:
            email_sent = send_password_reset_email(
                to_email=normalized,
                code=code,
                name=user.get("name"),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Could not send email. Check SMTP settings. ({exc})",
            ) from exc
    else:
        dev_code = code

    message = (
        "A 6-digit verification code was sent to your email."
        if email_sent
        else "SMTP is not configured. Use the development code shown below."
    )
    result: dict = {"message": message, "email_sent": email_sent}
    if dev_code and os.getenv("SMTP_EXPOSE_DEV_CODE", "true").strip().lower() in {"1", "true", "yes"}:
        result["dev_code"] = dev_code
    return result


def reset_password_with_code(*, email: str, code: str, new_password: str) -> dict:
    normalized = _normalize_email(email)
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    codes = _load_reset_codes()
    record = codes.get(normalized)
    if not record:
        raise HTTPException(status_code=400, detail="Request a new verification code first.")

    expires_at = datetime.fromisoformat(record["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        codes.pop(normalized, None)
        _save_reset_codes(codes)
        raise HTTPException(status_code=400, detail="Verification code expired. Request a new one.")

    if record.get("code") != code.strip():
        raise HTTPException(status_code=400, detail="Invalid verification code.")

    users = _load_users()
    user = users.get(normalized)
    if not user:
        raise HTTPException(status_code=404, detail="No account found with that email address.")

    user["hash_scheme"] = "bcrypt"
    user["password_hash"] = _hash_password_bcrypt(new_password)
    user.pop("salt", None)
    user["updated_at"] = datetime.now(timezone.utc).isoformat()
    users[normalized] = user
    _save_users(users)

    codes.pop(normalized, None)
    _save_reset_codes(codes)
    return {"ok": True, "message": "Password updated successfully."}


def verify_credentials(email: str, password: str) -> bool:
    normalized = _normalize_email(email)
    user = _load_users().get(normalized)
    if not user:
        return False
    return _verify_password(password, user)
