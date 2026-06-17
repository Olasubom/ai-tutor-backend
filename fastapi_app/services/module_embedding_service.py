"""PDF text extraction and per-module FAISS embeddings (separate from chat memory)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import faiss  # type: ignore
import numpy as np
from openai import OpenAI
from pypdf import PdfReader
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from agency.core.memory.vector_store import VectorStoreConfig
from agency.core.tools.database import Database
from agency.core.tools.models import ContentItem

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[2]
MODULE_EMBEDDINGS_DIR = Path(
    os.getenv("MODULE_EMBEDDINGS_DIR", str(_ROOT / "agency" / "data" / "memory" / "module_embeddings"))
)

PDF_SOURCE_TYPES = {"pdf", "document"}


def extract_pdf_text(file_path: str) -> str:
    try:
        reader = PdfReader(file_path)
        text_parts: List[str] = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        return "\n\n".join(text_parts).strip()
    except Exception as exc:
        logger.warning("[PDF EXTRACT ERROR] %s", exc)
        return ""


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Simple sliding-window chunking by words."""
    words = text.split()
    if not words:
        return []
    chunks: List[str] = []
    i = 0
    step = max(1, chunk_size - overlap)
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += step
    return chunks


class ModuleContentVectorStore:
    """
    FAISS-backed store for one content item's PDF chunks.

    Mirrors agency.core.memory.vector_store.VectorStore (IndexFlatIP + L2-normalized
    OpenAI embeddings) but lives under module_embeddings/{content_item_id}/ and does
    not mix with learner chat memory.
    """

    def __init__(self, content_item_id: str, cfg: Optional[VectorStoreConfig] = None):
        self.content_item_id = content_item_id
        base = MODULE_EMBEDDINGS_DIR / content_item_id
        self.cfg = cfg or VectorStoreConfig(
            base_dir=base,
            embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        self.base_dir = self.cfg.base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.base_dir / f"{content_item_id}.faiss"
        self.chunks_path = self.base_dir / f"{content_item_id}.json"
        self._api_key = os.getenv("OPENAI_API_KEY", "")
        self._embeddings_enabled = bool(self._api_key and "your_key_here" not in self._api_key.lower())
        self.client = OpenAI(api_key=self._api_key)
        self._index: Optional[faiss.Index] = None
        self._dim: Optional[int] = None
        self._chunks_cache: Optional[List[Dict[str, Any]]] = None

    def _load_chunks(self) -> List[Dict[str, Any]]:
        if self._chunks_cache is not None:
            return self._chunks_cache
        if not self.chunks_path.exists():
            self._chunks_cache = []
            return self._chunks_cache
        raw = json.loads(self.chunks_path.read_text(encoding="utf-8"))
        self._chunks_cache = raw if isinstance(raw, list) else []
        return self._chunks_cache

    def _save_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        self.chunks_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
        self._chunks_cache = chunks

    def _load_index(self) -> faiss.Index:
        if self._index is not None:
            return self._index
        if self.index_path.exists():
            self._index = faiss.read_index(str(self.index_path))
            self._dim = self._index.d
            return self._index
        self._index = faiss.IndexFlatIP(1536)
        self._dim = 1536
        return self._index

    def _persist_index(self) -> None:
        if self._index is not None:
            faiss.write_index(self._index, str(self.index_path))

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=1, max=10))
    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        if not self._embeddings_enabled:
            raise RuntimeError("OpenAI embeddings are disabled: API key is missing or placeholder.")
        resp = self.client.embeddings.create(model=self.cfg.embedding_model, input=list(texts))
        vectors = np.array([d.embedding for d in resp.data], dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12
        return vectors / norms

    def add_chunks(self, chunk_texts: List[str]) -> None:
        if not chunk_texts:
            return
        if not self._embeddings_enabled:
            logger.warning("module_embeddings_disabled", extra={"content_item_id": self.content_item_id})
            return

        vectors = self.embed_texts(chunk_texts)
        dim = int(vectors.shape[1])
        if self._index is None:
            self._index = faiss.IndexFlatIP(dim)
            self._dim = dim
        elif self._dim != dim:
            raise ValueError(f"Embedding dimension mismatch: got {dim}, expected {self._dim}")

        index = self._load_index()
        index.add(vectors)
        records = [
            {
                "content_item_id": self.content_item_id,
                "chunk_index": i,
                "chunk_text": text,
            }
            for i, text in enumerate(chunk_texts)
        ]
        self._save_chunks(records)
        self._persist_index()

    def search(self, query: str, top_k: int = 4) -> List[str]:
        if not self._embeddings_enabled or not self.index_path.exists():
            return []
        chunks = self._load_chunks()
        if not chunks:
            return []
        index = self._load_index()
        qvec = self.embed_texts([query])[0]
        k = min(top_k, len(chunks))
        scores, idxs = index.search(np.expand_dims(qvec, axis=0), k=k)
        out: List[str] = []
        for raw_i in idxs[0].tolist():
            if raw_i < 0 or raw_i >= len(chunks):
                continue
            text = chunks[raw_i].get("chunk_text", "")
            if text and text not in out:
                out.append(text)
        return out


def get_ordered_chunks(content_item_id: str) -> List[str]:
    store = ModuleContentVectorStore(content_item_id)
    records = store._load_chunks()
    sorted_records = sorted(records, key=lambda r: int(r.get("chunk_index", 0)))
    return [str(r.get("chunk_text", "")) for r in sorted_records if r.get("chunk_text")]


def retrieve_relevant_chunks(content_item_id: str, query: str, top_k: int = 4) -> List[str]:
    """Semantic search over a module's PDF embeddings."""
    db = Database()
    with db._SessionLocal() as session:  # noqa: SLF001
        item = session.get(ContentItem, content_item_id)
        if item is None or (item.embedding_status or "") != "embedded":
            return []
    store = ModuleContentVectorStore(content_item_id)
    return store.search(query, top_k=top_k)


def _resolve_file_path(content_item: ContentItem) -> Optional[str]:
    from fastapi_app.services import upload_service

    item_id = content_item.item_id
    if item_id.startswith("upload_"):
        upload_id = item_id.replace("upload_", "", 1)
        record = upload_service.get_material(upload_id)
        if record:
            return record.get("file_path")
    payload = dict(content_item.payload_json or {})
    return payload.get("file_path")


def _update_content_item_embedding(
    content_item_id: str,
    *,
    extracted_text: Optional[str] = None,
    embedding_status: str,
) -> None:
    db = Database()
    with db._SessionLocal() as session:  # noqa: SLF001
        item = session.get(ContentItem, content_item_id)
        if item is None:
            return
        if extracted_text is not None:
            item.extracted_text = extracted_text
        item.embedding_status = embedding_status
        session.commit()


def embed_content_item(content_item_id: str, text: str) -> None:
    """Chunk text and store embeddings in a dedicated FAISS index for this module."""
    if not text.strip():
        _update_content_item_embedding(content_item_id, embedding_status="failed")
        return
    try:
        chunks = chunk_text(text)
        if not chunks:
            _update_content_item_embedding(content_item_id, embedding_status="failed")
            return
        store = ModuleContentVectorStore(content_item_id)
        store.add_chunks(chunks)
        _update_content_item_embedding(content_item_id, embedding_status="embedded")
        logger.info("module_embedded", extra={"content_item_id": content_item_id, "chunks": len(chunks)})
    except Exception:
        logger.exception("module_embed_failed", extra={"content_item_id": content_item_id})
        _update_content_item_embedding(content_item_id, embedding_status="failed")


def process_content_item_embeddings(content_item_id: str) -> None:
    """Extract PDF text (if applicable) and embed for RAG."""
    db = Database()
    with db._SessionLocal() as session:  # noqa: SLF001
        item = session.get(ContentItem, content_item_id)
        if item is None:
            return
        source_type = (item.source_type or "").lower()
        if source_type not in PDF_SOURCE_TYPES:
            item.embedding_status = "skipped"
            session.commit()
            return

        if item.extracted_text and item.embedding_status == "embedded":
            return

        file_path = _resolve_file_path(item)
        if not file_path or not Path(file_path).exists():
            item.embedding_status = "failed"
            session.commit()
            return

        extracted = extract_pdf_text(file_path)
        item.extracted_text = extracted or None
        item.embedding_status = "pending"
        session.commit()

    if extracted:
        embed_content_item(content_item_id, extracted)
    else:
        _update_content_item_embedding(content_item_id, embedding_status="failed")


def get_embedding_status(content_item_id: str, db: Session) -> dict:
    """Return embedding_status for upload id or content item id."""
    resolved = content_item_id
    if not resolved.startswith("upload_"):
        resolved = f"upload_{content_item_id}"
    item = db.get(ContentItem, resolved)
    if item is None:
        item = db.get(ContentItem, content_item_id)
    if item is None:
        return {"content_item_id": content_item_id, "embedding_status": "unknown"}
    return {
        "content_item_id": item.item_id,
        "embedding_status": item.embedding_status or "pending",
        "has_extracted_text": bool(item.extracted_text),
    }
