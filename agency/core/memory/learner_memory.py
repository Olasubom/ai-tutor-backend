"""
Structured and short-term learner memory.

Long-term semantic memory is stored in VectorStore (FAISS). This module coordinates
reads/writes across short-term turns, structured JSON profiles, and optional vector updates.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

from agency.core.utils import utc_now

if TYPE_CHECKING:
    from agency.core.memory.vector_store import VectorStore
    from agency.core.tools.repository import LearnerRepository

logger = logging.getLogger(__name__)
SUPPORTED_MODALITIES = {"video", "text", "interactive", "game", "read_aloud"}

MemoryType = Literal[
    "preference",
    "performance",
    "weakness",
    "goal",
    "constraint",
    "milestone",
    "misconception",
    "plan",
]


class MemoryItem(BaseModel):
    """Canonical shape for a durable memory fact."""

    id: str
    learner_id: str
    created_at: datetime
    memory_type: MemoryType
    content: str
    topic_tags: List[str] = Field(default_factory=list)
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ShortTermTurn(BaseModel):
    """One turn in the short-term conversation log."""

    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime


@dataclass(frozen=True)
class LearnerMemoryPaths:
    """Filesystem paths for per-learner memory files."""

    base_dir: Path

    def short_term_path(self, learner_id: str) -> Path:
        return self.base_dir / "short_term" / f"{learner_id}.jsonl"

    def structured_profile_path(self, learner_id: str) -> Path:
        return self.base_dir / "profiles" / f"{learner_id}.json"


class LearnerMemory:
    """
  Lightweight structured + short-term memory.

  - Short-term turns: JSONL append-only log per learner.
  - Structured profile: JSON document per learner (mastery, tasks, preferences).
  - Vector store (optional): FAISS long-term semantic memory via VectorStore.
    """

    def __init__(
        self,
        base_dir: Path,
        short_term_max_turns: int = 20,
        vector_store: Optional["VectorStore"] = None,
        repository: Optional["LearnerRepository"] = None,
    ):
        self.paths = LearnerMemoryPaths(base_dir=base_dir)
        self.base_dir = base_dir
        self.short_term_max_turns = short_term_max_turns
        self._vector_store = vector_store
        self._repository = repository
        (self.base_dir / "short_term").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "profiles").mkdir(parents=True, exist_ok=True)

    def set_vector_store(self, vector_store: "VectorStore") -> None:
        """Attach or replace the vector store (called during runtime bootstrap)."""
        self._vector_store = vector_store

    def append_turn(
        self,
        learner_id: str,
        role: Literal["user", "assistant", "system"],
        content: str,
    ) -> None:
        """Append one conversation turn and trim to max length."""
        if self._repository is not None:
            try:
                self._repository.append_turn(learner_id=learner_id, role=role, content=content)
                return
            except Exception:
                logger.exception("db_append_turn_failed", extra={"learner_id": learner_id})

        turn = ShortTermTurn(role=role, content=content, created_at=utc_now())
        path = self.paths.short_term_path(learner_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(turn.model_dump_json() + "\n")
        self._trim_short_term(learner_id)

    def get_recent_turns(self, learner_id: str, n: int = 10) -> List[ShortTermTurn]:
        """Return the last n short-term turns (oldest-first within the window)."""
        if self._repository is not None:
            try:
                rows = self._repository.get_recent_turns(learner_id=learner_id, n=n)
                return [
                    ShortTermTurn(
                        role=str(r.get("role")),
                        content=str(r.get("content", "")),
                        created_at=r.get("created_at") or utc_now(),
                    )
                    for r in rows
                ]
            except Exception:
                logger.exception("db_get_recent_turns_failed", extra={"learner_id": learner_id})

        path = self.paths.short_term_path(learner_id)
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        turns: List[ShortTermTurn] = []
        for line in lines[-max(n, 0) :]:
            if not line.strip():
                continue
            try:
                turns.append(ShortTermTurn.model_validate_json(line))
            except Exception:
                logger.warning("Skipping corrupt short-term line", extra={"learner_id": learner_id})
        return turns

    def get_relevant_memory(
        self,
        learner_id: str,
        query: str,
        k: int = 5,
    ) -> Dict[str, Any]:
        """
        Retrieve a unified memory bundle for agent reasoning.

        Combines:
          - top-k vector memories (semantic),
          - recent short-term turns,
          - structured profile highlights (weak topics, preferences, modality).
        """
        profile = self.get_profile(learner_id)
        recent = self.get_recent_turns(learner_id, n=min(k, 10))

        vector_memories: List[Dict[str, Any]] = []
        if self._vector_store is not None:
            try:
                hits = self._vector_store.search(learner_id=learner_id, query=query, top_k=k)
                vector_memories = [
                    {
                        "content": rec.content,
                        "memory_type": rec.memory_type,
                        "topic_tags": rec.topic_tags,
                        "score": round(score, 4),
                        "source": rec.source,
                    }
                    for rec, score in hits
                ]
            except Exception:
                logger.exception(
                    "vector_memory_search_failed",
                    extra={"learner_id": learner_id},
                )

        summary = profile.get("knowledge_state_summary", {})
        preferences = profile.get("preferences", {})
        preferred_modalities = profile.get("preferred_modalities", [])

        return {
            "learner_id": learner_id,
            "query": query,
            "vector_memories": vector_memories,
            "recent_turns": [t.model_dump(mode="json") for t in recent],
            "profile_highlights": {
                "weak_topics": summary.get("weak_topics", []),
                "developing_topics": summary.get("developing_topics", []),
                "mastered_topics": summary.get("mastered_topics", []),
                "trend": summary.get("trend"),
                "preferences": preferences,
                "modality": preferences.get("modality") if isinstance(preferences, dict) else None,
                "preferred_modalities": preferred_modalities if isinstance(preferred_modalities, list) else [],
            },
        }

    def update_preferred_modalities(
        self,
        learner_id: str,
        modalities: List[str],
        confidence: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Update learner preferred modalities in structured profile and vector memory.

        Stores the normalized modalities in:
        - `preferred_modalities`: list[str]
        - `preferences.modality`: primary modality (first entry), for backward compatibility
        """
        cleaned: List[str] = []
        for raw in modalities:
            mod = str(raw).strip().lower()
            if mod in SUPPORTED_MODALITIES and mod not in cleaned:
                cleaned.append(mod)

        if not cleaned:
            logger.info(
                "preferred_modalities_not_updated",
                extra={"learner_id": learner_id, "reason": "no_supported_modalities"},
            )
            return self.get_profile(learner_id)

        patch = {
            "preferred_modalities": cleaned,
            "preferences": {
                "modality": cleaned[0],
                "modalities_confidence": float(confidence),
                "modalities_updated_at": utc_now().isoformat(),
            },
        }
        profile = self.upsert_profile(learner_id, patch)

        if self._vector_store is not None:
            try:
                self._vector_store.add_memory(
                    learner_id=learner_id,
                    content=f"Learner prefers modalities: {', '.join(cleaned)}.",
                    memory_type="preference",
                    topic_tags=cleaned,
                    source="learner_memory.update_preferred_modalities",
                    metadata={"confidence": float(confidence)},
                )
            except Exception:
                logger.exception(
                    "preferred_modalities_vector_write_failed",
                    extra={"learner_id": learner_id},
                )

        logger.info(
            "preferred_modalities_updated",
            extra={"learner_id": learner_id, "modalities": cleaned, "confidence": float(confidence)},
        )
        return profile

    def update_learner_profile(
        self,
        learner_id: str,
        events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Apply incoming events to short-term memory, structured profile, and vector store.

        Each event may include:
          - topic / skill_id
          - correct (bool)
          - role, content (for chat turns)
          - memory_type, content (for explicit memory writes)

        Returns the updated profile dict.
        """
        if not events:
            return self.get_profile(learner_id)

        profile_patch: Dict[str, Any] = {"last_event_batch_at": utc_now().isoformat()}
        vector_writes = 0
        max_vector_writes = 3

        for event in events:
            # Chat-style turn
            if "content" in event and "role" in event:
                self.append_turn(learner_id, event["role"], str(event["content"]))
                continue

            topic = str(event.get("topic") or event.get("skill_id") or "").strip()
            modality_hint = event.get("modality")
            if modality_hint:
                # Lightweight implicit-preference update from interaction modality.
                self.update_preferred_modalities(
                    learner_id=learner_id,
                    modalities=[str(modality_hint)],
                    confidence=0.6,
                )
            if topic and "correct" in event:
                correct = bool(event.get("correct"))
                summary_line = (
                    f"Performance on {topic}: {'correct' if correct else 'incorrect'}."
                )
                self.append_turn(learner_id, "system", summary_line)

                if not correct and self._vector_store and vector_writes < max_vector_writes:
                    try:
                        self._vector_store.add_memory(
                            learner_id=learner_id,
                            content=f"Learner struggled with {topic} in a recent activity.",
                            memory_type="weakness",
                            topic_tags=[topic],
                            source="learner_memory.update_learner_profile",
                        )
                        vector_writes += 1
                    except Exception:
                        logger.exception(
                            "vector_write_failed",
                            extra={"learner_id": learner_id, "topic": topic},
                        )

            # Explicit durable memory from caller
            if event.get("content") and event.get("memory_type") and self._vector_store:
                if vector_writes < max_vector_writes:
                    try:
                        self._vector_store.add_memory(
                            learner_id=learner_id,
                            content=str(event["content"]),
                            memory_type=str(event["memory_type"]),
                            topic_tags=list(event.get("topic_tags") or []),
                            source=str(event.get("source", "learner_memory")),
                        )
                        vector_writes += 1
                    except Exception:
                        logger.exception("explicit_vector_write_failed", extra={"learner_id": learner_id})

        profile = self.upsert_profile(learner_id, profile_patch)
        logger.info(
            "learner_profile_updated",
            extra={
                "learner_id": learner_id,
                "event_count": len(events),
                "vector_writes": vector_writes,
            },
        )
        return profile

    def _trim_short_term(self, learner_id: str) -> None:
        if self.short_term_max_turns <= 0:
            return
        path = self.paths.short_term_path(learner_id)
        if not path.exists():
            return
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= self.short_term_max_turns:
            return
        trimmed = lines[-self.short_term_max_turns :]
        path.write_text("\n".join(trimmed) + "\n", encoding="utf-8")

    def get_profile(self, learner_id: str) -> Dict[str, Any]:
        if self._repository is not None:
            try:
                return self._repository.get_profile(learner_id=learner_id)
            except Exception:
                logger.exception("db_profile_read_failed", extra={"learner_id": learner_id})

        path = self.paths.structured_profile_path(learner_id)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("profile_read_failed", extra={"learner_id": learner_id})
            return {}

    def upsert_profile(self, learner_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        profile = self.get_profile(learner_id)
        profile = deep_merge(profile, patch)

        if self._repository is not None:
            try:
                return self._repository.upsert_profile(learner_id=learner_id, profile=profile)
            except Exception:
                logger.exception("db_profile_write_failed", extra={"learner_id": learner_id})

        path = self.paths.structured_profile_path(learner_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        return profile

    def reset_learner(self, learner_id: str) -> Dict[str, Any]:
        """Delete learner state from DB/file-backed profile and short-term memory."""
        result: Dict[str, Any] = {"learner_id": learner_id, "storage": "file", "deleted": {}}
        if self._repository is not None:
            try:
                counts = self._repository.reset_learner(learner_id)
                return {
                    "learner_id": learner_id,
                    "storage": "database",
                    "deleted": counts,
                }
            except Exception:
                logger.exception("db_reset_learner_failed", extra={"learner_id": learner_id})

        short_term = self.paths.short_term_path(learner_id)
        profile = self.paths.structured_profile_path(learner_id)
        deleted = {"short_term": False, "profile": False}
        if short_term.exists():
            short_term.unlink()
            deleted["short_term"] = True
        if profile.exists():
            profile.unlink()
            deleted["profile"] = True
        result["deleted"] = deleted
        return result


def deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge patch into base (patch wins on scalar conflicts)."""
    out = dict(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out
