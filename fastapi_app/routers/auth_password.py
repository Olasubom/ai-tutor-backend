from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field

from fastapi_app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=2)
    role: str = "student"


class SyncCredentialsRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: Optional[str] = None
    role: str = "student"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8)


@router.post("/login")
def login(payload: LoginRequest) -> dict:
    return auth_service.login(email=str(payload.email), password=payload.password)


@router.post("/register")
def register(payload: RegisterRequest) -> dict:
    return auth_service.register(
        email=str(payload.email),
        password=payload.password,
        name=payload.name,
        role=payload.role,
    )


@router.post("/sync-credentials")
def sync_credentials(payload: SyncCredentialsRequest) -> dict:
    """Upsert email/password hash when users register or sign in."""
    return auth_service.sync_credentials(
        email=str(payload.email),
        password=payload.password,
        name=payload.name,
        role=payload.role,
    )


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest) -> dict:
    """Generate a reset code and email it via Gmail SMTP."""
    return auth_service.request_password_reset(str(payload.email))


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest) -> dict:
    """Verify code and set a new password."""
    return auth_service.reset_password_with_code(
        email=str(payload.email),
        code=payload.code,
        new_password=payload.new_password,
    )
