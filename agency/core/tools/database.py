from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


@dataclass(frozen=True)
class DatabaseConfig:
    url: str = ""


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


class Database:
    def __init__(self, cfg: Optional[DatabaseConfig] = None):
        url = (cfg.url if cfg else None) or os.getenv("DATABASE_URL") or ""
        # DB is optional until you configure it; default to SQLite for local dev.
        if not url:
            url = "sqlite:///./ai_tutor.db"
        url = normalize_database_url(url)
        self.engine = create_engine(url, pool_pre_ping=True, future=True)
        self._SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

    def session(self) -> Generator[Session, None, None]:
        db = self._SessionLocal()
        try:
            yield db
        finally:
            db.close()

