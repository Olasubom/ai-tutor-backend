from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException

from fastapi_app.auth.utils import decode_token, optional_current_user


def _is_true(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class AuthContext:
    mode: str  # "jwt" | "api_key" | "none"
    user_id: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None


def require_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
    """
    Optional API key guard for tutor endpoints.

    Controlled by:
    - API_AUTH_ENABLED=true|false
    - API_KEY=<secret>
    """
    if not _is_true(os.getenv("API_AUTH_ENABLED", "false")):
        return

    configured = os.getenv("API_KEY", "").strip()
    if not configured:
        raise HTTPException(status_code=503, detail="API auth enabled but API_KEY is not configured.")
    if x_api_key != configured:
        raise HTTPException(status_code=401, detail="Invalid API key.")


def require_dev_token(x_dev_token: Optional[str] = Header(default=None, alias="X-Dev-Token")) -> None:
    """
    Dev endpoint guard.

    Controlled by:
    - ALLOW_DEV_ENDPOINTS=true|false
    - DEV_TOKEN=<secret>
    """
    if not _is_true(os.getenv("ALLOW_DEV_ENDPOINTS", "false")):
        raise HTTPException(status_code=403, detail="Dev endpoints are disabled.")

    configured = os.getenv("DEV_TOKEN", "").strip()
    if not configured:
        raise HTTPException(status_code=503, detail="Dev endpoints enabled but DEV_TOKEN is not configured.")
    if x_dev_token != configured:
        raise HTTPException(status_code=401, detail="Invalid dev token.")


def get_auth_context(
    authorization: Annotated[Optional[str], Header()] = None,
    x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None,
    jwt_user: Annotated[Optional[dict], Depends(optional_current_user)] = None,
) -> AuthContext:
    """Resolve JWT or API-key auth. JWT takes precedence when Bearer token is present."""
    if jwt_user and jwt_user.get("user_id"):
        return AuthContext(
            mode="jwt",
            user_id=jwt_user["user_id"],
            role=jwt_user.get("role"),
            email=jwt_user.get("email"),
            name=jwt_user.get("name"),
        )
    if _is_true(os.getenv("API_AUTH_ENABLED", "false")):
        configured = os.getenv("API_KEY", "").strip()
        if configured and x_api_key == configured:
            return AuthContext(mode="api_key")
        raise HTTPException(status_code=401, detail="Authentication required")
    return AuthContext(mode="none")


def resolve_learner_id(auth: AuthContext, body_learner_id: str) -> str:
    """JWT students use token user_id; API key uses body learner_id."""
    if auth.mode == "jwt" and auth.role == "student":
        return auth.user_id or body_learner_id
    return body_learner_id


def assert_profile_access(auth: AuthContext, learner_id: str) -> None:
    if auth.mode == "jwt" and auth.role == "student" and auth.user_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only access your own profile.")
