from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from agency.core.tools.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # student | lecturer | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Student fields
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    college: Mapped[str | None] = mapped_column(String(255), nullable=True)
    academic_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Lecturer fields
    nuc_staff_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    lecturer_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
