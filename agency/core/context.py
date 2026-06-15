from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from agency.core.memory.graph_store import GraphStore
from agency.core.memory.learner_memory import LearnerMemory
from agency.core.memory.vector_store import VectorStore, VectorStoreConfig
from agency.core.tools.database import Database
from agency.core.tools.repository import LearnerRepository


@dataclass
class TutorRuntime:
    """Process-wide runtime holding memory stores and sample catalog."""

    agency_root: Path
    learner_memory: LearnerMemory
    vector_store: VectorStore
    graph_store: GraphStore
    repository: Optional[LearnerRepository] = None
    catalog: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(cls, agency_root: Optional[Path] = None) -> "TutorRuntime":
        root = agency_root or Path(__file__).resolve().parents[1]
        data_dir = root / "data"
        memory_dir = data_dir / "memory"
        vector_dir = Path(os.getenv("VECTOR_STORE_DIR", str(data_dir / "vector_store")))
        if not vector_dir.is_absolute():
            vector_dir = root / vector_dir

        short_term_max = int(os.getenv("SHORT_TERM_MAX_TURNS", "20"))
        embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

        vector_store = VectorStore(
            VectorStoreConfig(base_dir=vector_dir, embedding_model=embedding_model)
        )
        repository = None
        try:
            db = Database()
            repository = LearnerRepository(db)
            repository.create_tables()
        except Exception:
            # Keep application running with file-backed fallback if DB is unavailable.
            repository = None

        learner_memory = LearnerMemory(
            memory_dir,
            short_term_max_turns=short_term_max,
            vector_store=vector_store,
            repository=repository,
        )
        runtime = cls(
            agency_root=root,
            learner_memory=learner_memory,
            vector_store=vector_store,
            graph_store=GraphStore.empty(),
            repository=repository,
        )
        runtime._load_catalog()
        runtime._load_skill_graph()
        return runtime

    def _load_catalog(self) -> None:
        primary_path = self.agency_root / "data" / "learning_catalog.json"
        fallback_path = self.agency_root / "data" / "sample_data" / "learning_catalog.json"
        catalog_path = primary_path if primary_path.exists() else fallback_path
        if not catalog_path.exists():
            self.catalog = []
            return

        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
        # Accept both:
        # 1) {"catalog": [...]} (new format)
        # 2) [...] (legacy format)
        if isinstance(raw, dict) and isinstance(raw.get("catalog"), list):
            file_catalog = raw["catalog"]
        elif isinstance(raw, list):
            file_catalog = raw
        else:
            file_catalog = []

        # Enrich with source metadata defaults.
        enriched = [self._normalize_catalog_item(item) for item in file_catalog if isinstance(item, dict)]

        # DB-first catalog strategy:
        # 1) if DB has content_items, use them
        # 2) else seed DB from file and use seeded items
        # 3) fallback to file-only
        if self.repository is not None:
            try:
                if self.repository.content_item_count() == 0 and enriched:
                    self.repository.upsert_content_items(enriched)
                db_items = self.repository.list_content_items(limit=5000)
                if db_items:
                    self.catalog = db_items
                    return
            except Exception:
                # keep file-based fallback
                self.catalog = enriched
                return

        self.catalog = enriched

    def _normalize_catalog_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from fastapi_app.services.content_type import normalize_content_item

            return normalize_content_item(item)
        except Exception:
            normalized = dict(item)
            modality = str(item.get("modality", "")).lower()
            source_type = item.get("source_type")
            if not source_type:
                if modality in {"video"}:
                    source_type = "youtube"
                    normalized.setdefault("provider", "YouTube")
                elif modality in {"text", "read_aloud"}:
                    source_type = "ebook"
                    normalized.setdefault("provider", "OpenLibrary")
                elif modality in {"interactive", "game"}:
                    source_type = "internal"
                    normalized.setdefault("provider", "AI Tutor")
                else:
                    source_type = "internal"
            normalized.setdefault("source_type", source_type)
            normalized.setdefault("source_url", "")
            normalized.setdefault("quality_score", 0.6)
            normalized.setdefault("source_origin", "seeded")
            return normalized

    def _load_skill_graph(self) -> None:
        graph_path = self.agency_root / "data" / "sample_data" / "skill_graph.json"
        if not graph_path.exists():
            return
        edges = json.loads(graph_path.read_text(encoding="utf-8"))
        for edge in edges:
            self.graph_store.add_prereq(edge["prereq"], edge["skill"])


_runtime: Optional[TutorRuntime] = None


def get_runtime() -> TutorRuntime:
    global _runtime
    if _runtime is None:
        _runtime = TutorRuntime.create()
    return _runtime


def reset_runtime() -> None:
    """Reset runtime (useful in tests)."""
    global _runtime
    _runtime = None
