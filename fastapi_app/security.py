from __future__ import annotations

import os
from typing import Optional

from fastapi import Header, HTTPException


def _is_true(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
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


def require_dev_token(x_dev_token: Optional[str] = Header(default=None)) -> None:
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

