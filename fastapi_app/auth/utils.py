from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Callable, Dict, Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT_SECRET is not configured. Set a long random string in agency/.env",
        )
    return secret


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload["exp"] = expire
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc


def get_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
) -> Dict[str, Any]:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(token)
    if not payload.get("user_id"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return payload


def require_role(*roles: str) -> Callable:
    def _dep(user: Annotated[dict, Depends(get_current_user)]) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        return user

    return _dep


def optional_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    try:
        return decode_token(token)
    except HTTPException:
        return None
