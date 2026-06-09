"""Verify Google Sign-In ID tokens from the frontend."""

from __future__ import annotations

import os

from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token


def verify_google_credential(credential: str) -> dict:
    """
    Validate a Google ID token (JWT) from @react-oauth/google.

    Returns the decoded token claims (email, name, sub, etc.).
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID in agency/.env",
        )

    try:
        idinfo = id_token.verify_oauth2_token(credential, google_requests.Request(), client_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Google sign-in token.",
        ) from exc

    if not idinfo.get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account did not return an email address.",
        )

    if idinfo.get("email_verified") is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google email address is not verified.",
        )

    return idinfo
