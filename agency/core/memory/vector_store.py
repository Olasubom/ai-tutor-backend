from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import faiss  # type: ignore
import numpy as np
from openai import OpenAI
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from agency.core.utils import utc_now

logger = logging.getLogger(__name__)


class VectorMemoryRecord(BaseModel):
    id: str
    learner_id: str
    created_at: datetime
    content: str
    memory_type: str
    topic_tags: List[str] = Field(default_factory=list)
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class VectorStoreConfig:
    base_dir: Path
    embedding_model: str = "text-embedding-3-small"


class VectorStore:
    """
    FAISS-backed vector store with a JSONL metadata sidecar.

    - Uses L2-normalized vectors so dot-product approximates cosine similarity.
    - Stores vectors in an IndexFlatIP (inner product).
    - Stores metadata in `records.jsonl` with aligned insertion order.
    """

    def __init__(self, cfg: VectorStoreConfig, client: Optional[OpenAI] = None):
        self.cfg = cfg
        self.base_dir = cfg.base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.base_dir / "faiss.index"
        self.records_path = self.base_dir / "records.jsonl"
        self._api_key = os.getenv("OPENAI_API_KEY", "")
        self._embeddings_enabled = bool(self._api_key and "your_key_here" not in self._api_key.lower())
        self._disabled_warning_emitted = False
        self.client = client or OpenAI(api_key=self._api_key)

        self._index: Optional[faiss.Index] = None
        self._dim: Optional[int] = None
        self._records_cache: Optional[List[VectorMemoryRecord]] = None

    def _load_records(self) -> List[VectorMemoryRecord]:
        if self._records_cache is not None:
            return self._records_cache
        if not self.records_path.exists():
            self._records_cache = []
            return self._records_cache
        out: List[VectorMemoryRecord] = []
        for line in self.records_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            out.append(VectorMemoryRecord.model_validate_json(line))
        self._records_cache = out
        return out

    def _save_record(self, rec: VectorMemoryRecord) -> None:
        with self.records_path.open("a", encoding="utf-8") as f:
            f.write(rec.model_dump_json() + "\n")
        if self._records_cache is not None:
            self._records_cache.append(rec)

    def _load_index(self) -> faiss.Index:
        if self._index is not None:
            return self._index
        if self.index_path.exists():
            self._index = faiss.read_index(str(self.index_path))
            self._dim = self._index.d
            return self._index

        # lazily initialized on first add (once we know embedding dim)
        self._index = None
        return self._create_empty_index(dim=1536)  # safe default; corrected at first embed if needed

    def _create_empty_index(self, dim: int) -> faiss.Index:
        self._dim = dim
        index = faiss.IndexFlatIP(dim)
        self._index = index
        return index

    def _persist_index(self) -> None:
        if self._index is None:
            return
        faiss.write_index(self._index, str(self.index_path))

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=1, max=10))
    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        if not self._embeddings_enabled:
            raise RuntimeError("OpenAI embeddings are disabled: API key is missing or placeholder.")
        resp = self.client.embeddings.create(model=self.cfg.embedding_model, input=list(texts))
        vectors = np.array([d.embedding for d in resp.data], dtype=np.float32)
        # L2 normalize
        norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12
        return vectors / norms

    def add_memory(
        self,
        *,
        learner_id: str,
        content: str,
        memory_type: str,
        topic_tags: Optional[List[str]] = None,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
        memory_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> VectorMemoryRecord:
        rec = VectorMemoryRecord(
            id=memory_id or f"mem_{int(utc_now().timestamp()*1000)}",
            learner_id=learner_id,
            created_at=created_at or utc_now(),
            content=content,
            memory_type=memory_type,
            topic_tags=topic_tags or [],
            source=source,
            metadata=metadata or {},
        )
        if not self._embeddings_enabled:
            self._log_disabled_once("add_memory")
            return rec

        vec = self.embed_texts([self._embed_payload(rec)])[0]
        if self._index is None or self._dim is None:
            self._create_empty_index(dim=int(vec.shape[0]))
        elif int(vec.shape[0]) != int(self._dim):
            raise ValueError(f"Embedding dimension mismatch: got {vec.shape[0]}, expected {self._dim}")

        index = self._load_index()
        index.add(np.expand_dims(vec, axis=0))
        self._save_record(rec)
        self._persist_index()
        return rec

    def search(
        self,
        *,
        learner_id: str,
        query: str,
        top_k: int = 8,
        memory_types: Optional[List[str]] = None,
    ) -> List[Tuple[VectorMemoryRecord, float]]:
        if not self._embeddings_enabled:
            self._log_disabled_once("search")
            return []
        records = self._load_records()
        if not records:
            return []
        index = self._load_index()
        qvec = self.embed_texts([query])[0]
        scores, idxs = index.search(np.expand_dims(qvec, axis=0), k=min(top_k * 5, len(records)))
        scored: List[Tuple[VectorMemoryRecord, float]] = []
        for raw_i, raw_score in zip(idxs[0].tolist(), scores[0].tolist()):
            if raw_i < 0 or raw_i >= len(records):
                continue
            rec = records[raw_i]
            if rec.learner_id != learner_id:
                continue
            if memory_types and rec.memory_type not in memory_types:
                continue
            scored.append((rec, float(raw_score)))
            if len(scored) >= top_k:
                break
        return scored

    def _embed_payload(self, rec: VectorMemoryRecord) -> str:
        tags = ", ".join(rec.topic_tags) if rec.topic_tags else ""
        return f"[type={rec.memory_type}] [tags={tags}] {rec.content}"

    def _log_disabled_once(self, operation: str) -> None:
        if self._disabled_warning_emitted:
            return
        self._disabled_warning_emitted = True
        logger.warning(
            "vector_store_disabled",
            extra={
                "operation": operation,
                "reason": "OPENAI_API_KEY missing or placeholder; vector memory is in no-op mode",
            },
        )

