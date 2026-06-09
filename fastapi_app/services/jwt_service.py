"""JWT access tokens for authenticated API sessions."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import HTTPException
from jose import JWTError, jwt

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="JWT_SECRET is not configured. Set a long random string in agency/.env",
        )
    return secret


def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    )
    payload["exp"] = expire
    return jwt.encode(payload, get_jwt_secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, get_jwt_secret(), algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
