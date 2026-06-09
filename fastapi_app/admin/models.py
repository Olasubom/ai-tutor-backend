from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agency.core.tools.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AdminNucId(Base):
    __tablename__ = "admin_nuc_ids"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nuc_staff_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    college: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class College(Base):
    __tablename__ = "colleges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    college_id: Mapped[str] = mapped_column(String(36), ForeignKey("colleges.id"), nullable=False)


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    course_code: Mapped[str] = mapped_column(String(64), nullable=False)
    course_title: Mapped[str] = mapped_column(String(255), nullable=False)
    department_id: Mapped[str] = mapped_column(String(36), ForeignKey("departments.id"), nullable=False)
    level: Mapped[str] = mapped_column(String(8), nullable=False)
    credit_units: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    semester: Mapped[str] = mapped_column(String(16), default="First", nullable=False)
    course_type: Mapped[str] = mapped_column(String(32), default="Compulsory", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
