from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agency.core.tools.database import Base


class Learner(Base):
    __tablename__ = "learners"

    learner_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    profile_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    interactions: Mapped[list["Interaction"]] = relationship(back_populates="learner")


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learners.learner_id"), index=True)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    learner: Mapped["Learner"] = relationship(back_populates="interactions")


class TopicMastery(Base):
    __tablename__ = "topic_mastery"
    __table_args__ = (UniqueConstraint("learner_id", "topic", name="uq_topic_mastery_learner_topic"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learners.learner_id"), index=True)
    topic: Mapped[str] = mapped_column(String(255), index=True)
    p_l: Mapped[float] = mapped_column(Float, default=0.0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    state_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Task(Base):
    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learners.learner_id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    estimated_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class ContentItem(Base):
    __tablename__ = "content_items"

    item_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    topic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    modality: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    bloom_level: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    provider: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    payload_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    topics_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    requested_count: Mapped[int] = mapped_column(Integer, default=0)
    fetched_count: Mapped[int] = mapped_column(Integer, default=0)
    deduped_count: Mapped[int] = mapped_column(Integer, default=0)
    written_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="success", index=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

