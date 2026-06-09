"""Shared SQLAlchemy engine and session for FastAPI dependencies."""

from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from agency.core.tools.database import Base, Database

_db = Database()


def get_engine():
    return _db.engine


def get_db() -> Generator[Session, None, None]:
    yield from _db.session()


__all__ = ["Base", "get_db", "get_engine", "Database"]
