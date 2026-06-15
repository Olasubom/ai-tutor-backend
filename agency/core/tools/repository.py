from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from agency.core.tools.database import Base, Database
from agency.core.tools.models import ContentItem, IngestionRun, Interaction, Learner, Task, TopicMastery

logger = logging.getLogger(__name__)


class LearnerRepository:
    """DB repository for learner profile, interactions, mastery, and tasks."""

    def __init__(self, db: Database):
        self.db = db

    def create_tables(self) -> None:
        Base.metadata.create_all(bind=self.db.engine)

    @contextmanager
    def _session(self) -> Generator[Session, None, None]:
        session = self.db._SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def ensure_learner(self, learner_id: str) -> None:
        with self._session() as s:
            learner = s.get(Learner, learner_id)
            if learner is None:
                s.add(Learner(learner_id=learner_id, profile_json={}))

    def get_profile(self, learner_id: str) -> Dict[str, Any]:
        with self._session() as s:
            learner = s.get(Learner, learner_id)
            return dict(learner.profile_json or {}) if learner else {}

    def upsert_profile(self, learner_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        with self._session() as s:
            learner = s.get(Learner, learner_id)
            if learner is None:
                learner = Learner(learner_id=learner_id, profile_json={})
                s.add(learner)
            learner.profile_json = profile
        # sync derived tables outside transaction boundary of caller
        self.sync_topic_mastery(learner_id, profile.get("topic_mastery", {}))
        self.sync_tasks(learner_id, profile.get("tasks", []))
        return profile

    def append_turn(self, learner_id: str, role: str, content: str, created_at: Optional[datetime] = None) -> None:
        self.ensure_learner(learner_id)
        with self._session() as s:
            s.add(
                Interaction(
                    learner_id=learner_id,
                    role=role,
                    content=content,
                    created_at=created_at or datetime.utcnow(),
                )
            )

    def get_recent_turns(self, learner_id: str, n: int = 10) -> List[Dict[str, Any]]:
        with self._session() as s:
            stmt = (
                select(Interaction)
                .where(Interaction.learner_id == learner_id)
                .order_by(Interaction.created_at.desc())
                .limit(max(n, 0))
            )
            rows = list(s.scalars(stmt).all())
            rows.reverse()
            return [
                {
                    "role": r.role,
                    "content": r.content,
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    def sync_topic_mastery(self, learner_id: str, topic_mastery: Dict[str, Any]) -> None:
        if not isinstance(topic_mastery, dict):
            return
        with self._session() as s:
            for topic, state in topic_mastery.items():
                if not isinstance(state, dict):
                    continue
                stmt = select(TopicMastery).where(
                    TopicMastery.learner_id == learner_id, TopicMastery.topic == str(topic)
                )
                row = s.scalars(stmt).first()
                if row is None:
                    row = TopicMastery(learner_id=learner_id, topic=str(topic))
                    s.add(row)
                row.state_json = state
                row.p_l = float(state.get("p_l", 0.0))
                row.attempts = int(state.get("attempts", 0))
                row.correct_count = int(state.get("correct_count", 0))

    def sync_tasks(self, learner_id: str, tasks: List[Dict[str, Any]]) -> None:
        if not isinstance(tasks, list):
            return
        with self._session() as s:
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                task_id = str(task.get("task_id") or "")
                if not task_id:
                    continue
                row = s.get(Task, task_id)
                if row is None:
                    row = Task(task_id=task_id, learner_id=learner_id, title=str(task.get("title", task_id)))
                    s.add(row)
                row.learner_id = learner_id
                row.title = str(task.get("title", row.title))
                row.priority = str(task.get("priority")) if task.get("priority") is not None else None
                row.status = str(task.get("status")) if task.get("status") is not None else None
                row.estimated_minutes = (
                    int(task.get("estimated_minutes")) if task.get("estimated_minutes") is not None else None
                )
                row.payload_json = task
                due_raw = task.get("due_date")
                if isinstance(due_raw, str):
                    try:
                        row.due_date = date.fromisoformat(due_raw)
                    except ValueError:
                        row.due_date = None

    def reset_learner(self, learner_id: str) -> Dict[str, int]:
        """Delete learner-specific persistence rows for clean testing."""
        counts = {"interactions": 0, "topic_mastery": 0, "tasks": 0, "learners": 0}
        with self._session() as s:
            interactions_deleted = s.execute(
                delete(Interaction).where(Interaction.learner_id == learner_id)
            )
            counts["interactions"] = int(interactions_deleted.rowcount or 0)

            mastery_deleted = s.execute(
                delete(TopicMastery).where(TopicMastery.learner_id == learner_id)
            )
            counts["topic_mastery"] = int(mastery_deleted.rowcount or 0)

            tasks_deleted = s.execute(delete(Task).where(Task.learner_id == learner_id))
            counts["tasks"] = int(tasks_deleted.rowcount or 0)

            learner_deleted = s.execute(delete(Learner).where(Learner.learner_id == learner_id))
            counts["learners"] = int(learner_deleted.rowcount or 0)
        return counts

    def upsert_content_items(self, items: List[Dict[str, Any]]) -> int:
        """Insert/update content items used by recommendation engine."""
        written = 0
        with self._session() as s:
            pending: Dict[str, ContentItem] = {}
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get("id") or item.get("item_id") or "").strip()
                title = str(item.get("title") or "").strip()
                if not item_id or not title:
                    continue

                row = s.get(ContentItem, item_id)
                if row is None:
                    row = pending.get(item_id)
                if row is None:
                    row = ContentItem(item_id=item_id, title=title)
                    s.add(row)
                    pending[item_id] = row
                row.title = title
                row.topic = str(item.get("topic")) if item.get("topic") is not None else None
                row.modality = str(item.get("modality")) if item.get("modality") is not None else None
                row.difficulty = str(item.get("difficulty")) if item.get("difficulty") is not None else None
                row.bloom_level = str(item.get("bloom_level")) if item.get("bloom_level") is not None else None
                row.source_type = str(item.get("source_type")) if item.get("source_type") is not None else None
                row.provider = str(item.get("provider")) if item.get("provider") is not None else None
                row.source_url = str(item.get("source_url")) if item.get("source_url") is not None else None
                row.quality_score = (
                    float(item.get("quality_score")) if item.get("quality_score") is not None else None
                )
                if item.get("course_id") is not None:
                    row.course_id = str(item.get("course_id"))
                if item.get("module_order") is not None:
                    row.module_order = int(item.get("module_order"))
                if item.get("status") is not None:
                    row.status = str(item.get("status"))
                elif row.status is None:
                    row.status = "approved"
                if item.get("uploaded_by") is not None:
                    row.uploaded_by = str(item.get("uploaded_by"))
                row.payload_json = item
                written += 1
        return written

    def list_content_items(
        self,
        limit: int = 1000,
        topic: Optional[str] = None,
        modality: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self._session() as s:
            stmt = select(ContentItem)
            if topic:
                stmt = stmt.where(ContentItem.topic == topic)
            if modality:
                stmt = stmt.where(ContentItem.modality == modality)
            if source_type:
                stmt = stmt.where(ContentItem.source_type == source_type)
            stmt = stmt.order_by(ContentItem.updated_at.desc()).limit(max(limit, 1))
            rows = list(s.scalars(stmt).all())
            out: List[Dict[str, Any]] = []
            for row in rows:
                payload = dict(row.payload_json or {})
                payload.setdefault("id", row.item_id)
                payload.setdefault("title", row.title)
                payload.setdefault("topic", row.topic)
                payload.setdefault("modality", row.modality)
                payload.setdefault("difficulty", row.difficulty)
                payload.setdefault("bloom_level", row.bloom_level)
                payload.setdefault("source_type", row.source_type)
                payload.setdefault("provider", row.provider)
                payload.setdefault("source_url", row.source_url)
                payload.setdefault("quality_score", row.quality_score)
                payload.setdefault("course_id", row.course_id)
                payload.setdefault("module_order", row.module_order)
                payload.setdefault("status", row.status)
                payload.setdefault("uploaded_by", row.uploaded_by)
                out.append(payload)
            return out

    def content_item_count(self) -> int:
        with self._session() as s:
            return len(list(s.scalars(select(ContentItem.item_id)).all()))

    def backfill_source_origin(self) -> Dict[str, int]:
        """
        Set source_origin on existing content_items missing it.

        Heuristic:
        - ids starting with yt_ or book_ => ingested
        - everything else => seeded
        """
        counts = {"updated": 0, "seeded": 0, "ingested": 0, "skipped": 0}
        with self._session() as s:
            rows = list(s.scalars(select(ContentItem)).all())
            for row in rows:
                payload = dict(row.payload_json or {})
                if str(payload.get("source_origin", "")).strip():
                    counts["skipped"] += 1
                    continue

                item_id = str(row.item_id or "")
                if item_id.startswith(("yt_", "book_")):
                    origin = "ingested"
                    counts["ingested"] += 1
                else:
                    origin = "seeded"
                    counts["seeded"] += 1

                payload["source_origin"] = origin
                row.payload_json = payload
                counts["updated"] += 1
        return counts

    def create_ingestion_run(
        self,
        *,
        source: str,
        topics: List[str],
        requested_count: int,
        fetched_count: int,
        deduped_count: int,
        written_count: int,
        status: str,
        error: Optional[str] = None,
    ) -> int:
        with self._session() as s:
            row = IngestionRun(
                source=source,
                topics_json={"topics": topics},
                requested_count=max(0, int(requested_count)),
                fetched_count=max(0, int(fetched_count)),
                deduped_count=max(0, int(deduped_count)),
                written_count=max(0, int(written_count)),
                status=status,
                error=error,
            )
            s.add(row)
            s.flush()
            return int(row.id)

    def list_ingestion_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._session() as s:
            stmt = select(IngestionRun).order_by(IngestionRun.created_at.desc()).limit(max(1, int(limit)))
            rows = list(s.scalars(stmt).all())
            return [
                {
                    "id": int(r.id),
                    "source": r.source,
                    "topics": list((r.topics_json or {}).get("topics", [])),
                    "requested_count": int(r.requested_count or 0),
                    "fetched_count": int(r.fetched_count or 0),
                    "deduped_count": int(r.deduped_count or 0),
                    "written_count": int(r.written_count or 0),
                    "status": r.status,
                    "error": r.error,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]

