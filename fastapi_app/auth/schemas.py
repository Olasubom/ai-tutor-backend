from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class StudentRegister(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=8)
    department: str = ""
    college: str = ""
    academic_level: str = ""
    institution: str = ""


class LecturerRegister(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=8)
    nuc_staff_id: str
    college: str
    department: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    credential: str = Field(min_length=10)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    name: str
    email: str


class UserProfile(BaseModel):
    user_id: str
    email: str
    name: str
    role: str
    department: Optional[str] = None
    college: Optional[str] = None
    academic_level: Optional[str] = None
    institution: Optional[str] = None
    nuc_staff_id: Optional[str] = None
    is_verified: bool = True
    courses: List[str] = Field(default_factory=list)
    preferences: dict = Field(default_factory=dict)


class ProfilePatch(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    college: Optional[str] = None
    academic_level: Optional[str] = None
    institution: Optional[str] = None


class SubjectRating(BaseModel):
    topic: str
    proficiency: str


class OnboardingCompleteRequest(BaseModel):
    name: str = ""
    department: str
    college: str
    academic_level: str
    institution: str
    selected_course_ids: List[str] = Field(default_factory=list)
    subject_ratings: List[SubjectRating] = Field(default_factory=list)
    weekly_hours: int = 20
    content_formats: List[str] = Field(default_factory=list)
    primary_objective: str = "Academic Excellence"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8)


class BootstrapRequest(BaseModel):
    bootstrap_key: str
    email: EmailStr
    password: str = Field(min_length=8)
    name: Optional[str] = None


class AdminForgotPasswordRequest(BaseModel):
    email: EmailStr


class AdminVerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class AdminResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8)
