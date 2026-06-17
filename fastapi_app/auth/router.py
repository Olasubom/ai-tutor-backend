from __future__ import annotations

import logging
import os
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.admin.models import AdminNucId
from fastapi_app.auth import memory as learner_memory
from fastapi_app.auth.models import User
from pydantic import BaseModel, EmailStr, Field

from fastapi_app.auth.google_oauth import verify_google_credential
from fastapi_app.auth.schemas import (
    AdminForgotPasswordRequest,
    AdminResetPasswordRequest,
    AdminVerifyResetCodeRequest,
    BootstrapRequest,
    ForgotPasswordRequest,
    GoogleAuthRequest,
    LecturerRegister,
    LoginRequest,
    OnboardingCompleteRequest,
    ProfilePatch,
    ResetPasswordRequest,
    StudentRegister,
    TokenResponse,
    UserProfile,
)
from fastapi_app.auth.utils import (
    create_token,
    get_current_user,
    hash_password,
    require_role,
    verify_password,
)
from fastapi_app.database import get_db
from fastapi_app.services import auth_service as legacy_auth
from fastapi_app.services import admin_password_service

router = APIRouter(prefix="/auth", tags=["Auth"])


def _token_response(user: User) -> TokenResponse:
    token = create_token(
        {
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "name": user.name,
        }
    )
    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.id,
        name=user.name,
        email=user.email,
    )


def _user_profile(user: User) -> UserProfile:
    mem = learner_memory.get_structured_memory(user.id)
    return UserProfile(
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        department=user.department,
        college=user.college,
        academic_level=user.academic_level,
        institution=user.institution,
        nuc_staff_id=user.nuc_staff_id,
        is_verified=user.is_verified,
        courses=list(mem.get("courses") or []),
        preferences=dict(mem.get("preferences") or {}),
    )


@router.post("/register/student", response_model=TokenResponse)
def register_student(payload: StudentRegister, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    email = payload.email.lower().strip()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = User(
        email=email,
        name=payload.name.strip(),
        hashed_password=hash_password(payload.password),
        role="student",
        is_active=True,
        is_verified=True,
        department=payload.department or None,
        college=payload.college or None,
        academic_level=payload.academic_level or None,
        institution=payload.institution or None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    learner_memory.init_structured_memory(user.id, user.name)
    return _token_response(user)


@router.post("/register/lecturer", status_code=status.HTTP_202_ACCEPTED)
def register_lecturer(payload: LecturerRegister, db: Annotated[Session, Depends(get_db)]) -> dict:
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    nuc = db.scalar(
        select(AdminNucId).where(
            AdminNucId.nuc_staff_id == payload.nuc_staff_id.strip().upper(),
            AdminNucId.status == "active",
        )
    )
    if not nuc:
        raise HTTPException(
            status_code=400,
            detail="Staff ID not recognized. Contact your college administrator.",
        )

    user = User(
        email=email,
        name=payload.name.strip(),
        hashed_password=hash_password(payload.password),
        role="lecturer",
        is_active=True,
        is_verified=False,
        lecturer_status="pending_verification",
        nuc_staff_id=payload.nuc_staff_id.strip().upper(),
        college=payload.college,
        department=payload.department,
    )
    db.add(user)
    db.commit()
    return {
        "message": (
            "Your account is pending administrator approval. "
            "You will receive confirmation once verified."
        )
    }


@router.post("/google", response_model=TokenResponse)
def google_login(payload: GoogleAuthRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    """Sign in or register via Google ID token from the frontend."""
    idinfo = verify_google_credential(payload.credential)
    email = str(idinfo["email"]).lower().strip()
    name = str(idinfo.get("name") or email.split("@")[0]).strip()

    user = db.scalar(select(User).where(User.email == email))
    if user:
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account disabled.")
        if user.role == "lecturer" and not user.is_verified:
            raise HTTPException(
                status_code=403,
                detail="Your account is pending verification.",
            )
        mem = learner_memory.get_structured_memory(user.id)
        if not mem.get("onboarding_complete") and name and user.name != name:
            user.name = name
            db.commit()
    else:
        user = User(
            email=email,
            name=name,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            role="student",
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        learner_memory.init_structured_memory(user.id, user.name)

    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if user.role == "lecturer" and not user.is_verified:
        raise HTTPException(status_code=403, detail="Your account is pending verification.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled.")
    return _token_response(user)


@router.get("/me", response_model=UserProfile)
def me(
    current: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserProfile:
    user = db.get(User, current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_profile(user)


@router.patch("/profile", response_model=UserProfile)
def patch_profile(
    payload: ProfilePatch,
    current: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserProfile:
    user = db.get(User, current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    learner_memory.update_structured_memory(
        user.id,
        {
            k: v
            for k, v in {
                "name": user.name,
                "department": user.department,
                "college": user.college,
                "academic_level": user.academic_level,
                "institution": user.institution,
            }.items()
            if v is not None
        },
    )
    return _user_profile(user)


@router.post("/onboarding/complete")
def complete_onboarding(
    payload: OnboardingCompleteRequest,
    current: Annotated[dict, Depends(require_role("student"))],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    user = db.get(User, current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.name.strip():
        user.name = payload.name.strip()
    user.department = payload.department
    user.college = payload.college
    user.academic_level = payload.academic_level
    user.institution = payload.institution
    db.commit()
    learner_memory.update_structured_memory(
        user.id,
        {
            "name": user.name,
            "department": payload.department,
            "college": payload.college,
            "academic_level": payload.academic_level,
            "institution": payload.institution,
            "courses": payload.selected_course_ids,
            "subject_ratings": [r.model_dump() for r in payload.subject_ratings],
            "preferences": {
                "weekly_hours": payload.weekly_hours,
                "content_formats": payload.content_formats,
                "primary_objective": payload.primary_objective,
            },
            "onboarding_complete": True,
        },
    )
    if payload.selected_course_ids:
        from fastapi_app.services.enrollment_service import sync_enrollments_for_student

        sync_enrollments_for_student(db, user.id, [str(i) for i in payload.selected_course_ids])
    from fastapi_app.services.onboarding_service import seed_knowledge

    seed_knowledge(user.id, [r.model_dump() for r in payload.subject_ratings])
    return {"status": "complete"}


@router.get("/onboarding/status")
def onboarding_status(current: Annotated[dict, Depends(require_role("student"))]) -> dict:
    return learner_memory.onboarding_status(current["user_id"])


class SyncCredentialsRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str | None = None
    role: str = "student"


@router.post("/sync-credentials")
def sync_credentials(payload: SyncCredentialsRequest, db: Annotated[Session, Depends(get_db)]) -> dict:
    """Upsert credentials in DB (and legacy file store for password-reset tests)."""
    email = payload.email.lower().strip()
    legacy_auth.sync_credentials(
        email=email,
        password=payload.password,
        name=payload.name,
        role=payload.role,
    )
    user = db.scalar(select(User).where(User.email == email))
    if user:
        user.hashed_password = hash_password(payload.password)
        if payload.name:
            user.name = payload.name.strip()
        user.role = payload.role
    else:
        user = User(
            email=email,
            name=(payload.name or "User").strip(),
            hashed_password=hash_password(payload.password),
            role=payload.role,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
    db.commit()
    return {"ok": True, "email": email}


@router.post("/bootstrap-admin")
def bootstrap_admin(payload: BootstrapRequest, db: Annotated[Session, Depends(get_db)]) -> dict:
    """
    Creates the first admin account.
    Only works if NO admin account exists yet.
    Disabled once an admin exists.
    """
    bootstrap_key = os.getenv("BOOTSTRAP_KEY", "change-me-in-production")
    if payload.bootstrap_key != bootstrap_key:
        raise HTTPException(status_code=403, detail="Invalid bootstrap key")

    existing_admin = db.scalar(select(User).where(User.role == "admin"))
    if existing_admin:
        raise HTTPException(
            status_code=409,
            detail="Admin account already exists. This endpoint is now disabled.",
        )

    email = str(payload.email).lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if user:
        user.role = "admin"
        user.is_verified = True
        user.is_active = True
        if payload.name:
            user.name = payload.name.strip()
        if not user.institution:
            user.institution = "Fountain University"
        db.commit()
        return {"message": f"Promoted {email} to admin", "action": "promoted"}

    new_admin = User(
        email=email,
        name=(payload.name or "Platform Administrator").strip(),
        hashed_password=hash_password(payload.password),
        role="admin",
        is_active=True,
        is_verified=True,
        institution="Fountain University",
    )
    db.add(new_admin)
    db.commit()
    return {"message": "Admin account created", "action": "created", "email": email}


# Legacy password-reset (SMTP) — kept for backward compatibility
@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest) -> dict:
    return legacy_auth.request_password_reset(str(payload.email))


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest) -> dict:
    return legacy_auth.reset_password_with_code(
        email=str(payload.email),
        code=payload.code,
        new_password=payload.new_password,
    )


@router.post("/admin/forgot-password")
def admin_forgot_password(
    payload: AdminForgotPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Send a one-time verification code to the admin's registered email."""
    return admin_password_service.request_admin_password_reset(str(payload.email), db)


@router.post("/admin/verify-reset-code")
def admin_verify_reset_code(payload: AdminVerifyResetCodeRequest) -> dict:
    """Validate the admin reset code before showing the new-password step."""
    admin_password_service.verify_admin_reset_code(str(payload.email), payload.code)
    return {"ok": True, "message": "Verification code accepted."}


@router.post("/admin/reset-password")
def admin_reset_password(
    payload: AdminResetPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Reset admin password after email verification."""
    return admin_password_service.reset_admin_password_with_code(
        email=str(payload.email),
        code=payload.code,
        new_password=payload.new_password,
        db=db,
    )
