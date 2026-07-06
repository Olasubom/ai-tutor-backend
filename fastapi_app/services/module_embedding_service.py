"""PDF text extraction and per-module FAISS embeddings (separate from chat memory)."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
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

_ARABIC_RANGE = re.compile(r"[\u0600-\u06FF]")


def _topics_json_path(content_item_id: str) -> Path:
    return MODULE_EMBEDDINGS_DIR / content_item_id / "topics.json"


def _call_llm(user_prompt: str, max_tokens: int = 800) -> str:
    """LLM call for embed-time topic segmentation (mirrors module_session_service pattern)."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or "your_key" in api_key.lower():
        return ""
    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", os.getenv("OPENAI_FAST_MODEL", "gpt-4o"))
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Return valid JSON only when asked."},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        logger.exception("module_topic_llm_failed")
        return ""


def _detect_script(text: str) -> str:
    """Quick check for non-Latin script content to route segmentation strategy."""
    sample = text[:2000]
    if not sample:
        return "latin"
    arabic_chars = len(_ARABIC_RANGE.findall(sample))
    if arabic_chars > len(sample) * 0.15:
        return "arabic"
    return "latin"


def _regex_segment_topics(extracted_text: str) -> List[dict]:
    """
    Fast-path heuristic for Western-numbered, Latin-script documents.
    Splits ONLY on top-level numbered headings (1., 2., 3. — not 1.1, 2.3).
    Returns [] if fewer than 2 confident topic boundaries.
    """
    if not extracted_text or not extracted_text.strip():
        return []

    normalized = extracted_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")

    top_level_heading = re.compile(
        r"^\s*(\d+)\.\s+([A-Z][A-Za-z0-9 ,&\-/'’]{2,90})\s*$"
    )

    heading_line_indices: List[int] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 100:
            continue
        if top_level_heading.match(stripped):
            heading_line_indices.append(i)

    topics: List[dict] = []
    if heading_line_indices:
        for idx, start in enumerate(heading_line_indices):
            end = heading_line_indices[idx + 1] if idx + 1 < len(heading_line_indices) else len(lines)
            title_line = lines[start].strip()
            content = "\n".join(lines[start + 1 : end]).strip()
            if content:
                topics.append({"title": title_line, "content": content})

    return topics


def _llm_segment_topics(extracted_text: str, module_title: str, course_title: str) -> List[dict]:
    """
    Language-agnostic, format-agnostic topic segmentation.
    The LLM reads the full document and returns each topic's title AND
    full content directly — no text-slicing or marker-matching required.
    Works for any script (Arabic, Latin), any heading convention, any
    department at Fountain University.

    Runs ONCE at embed time and is cached — no cost during student sessions.
    """
    max_chars = 12000
    text_to_send = extracted_text[:max_chars]
    truncated = len(extracted_text) > max_chars

    prompt = f"""You are segmenting a university course document into teachable sections.
The document may be in English, Arabic, or mixed language.
Headings may be numbered, lettered, bold, or implicit topic shifts with no heading at all.

MODULE: {module_title}
COURSE: {course_title}
{"NOTE: document was truncated to first 12000 characters due to length." if truncated else ""}

DOCUMENT:
{text_to_send}

Task: Divide this document into between 3 and 10 teachable sections.
Each section should be one coherent topic — not too granular (don't split
every paragraph), not too broad (don't put everything in one section).

For each section:
- "title": a short, clear title for what this section covers (can be the
  original heading, or a concise label you create if there is no heading)
- "content": the COMPLETE text of this section, copied WORD FOR WORD from
  the document above — do not paraphrase, summarize, or add anything.
  Include all sub-headings, case names, examples, and bullet points that
  belong to this section.

CRITICAL: the "content" fields must together cover the entire document
with no content skipped or repeated. Every sentence in the document must
appear in exactly one section's content.

Return ONLY valid JSON — no markdown fences, no preamble:
{{
  "topics": [
    {{"title": "section title", "content": "complete section text verbatim"}}
  ]
}}"""

    raw = _call_llm(prompt, max_tokens=4000)

    try:
        clean = re.sub(r"```json|```", "", raw).strip()
        parsed = json.loads(clean)
        topics = parsed.get("topics", [])
    except Exception as e:
        logger.warning("[LLM SEGMENT PARSE ERROR] %s", e)
        return []

    valid = [t for t in topics if t.get("title") and t.get("content", "").strip()]

    if not valid:
        return []

    if len(valid) > 1:
        total_len = sum(len(t["content"]) for t in valid)
        first_len = len(valid[0]["content"])
        if total_len > 0 and first_len / total_len > 0.70:
            logger.warning(
                "[LLM SEGMENT] First topic = %s%% of content — LLM grouping failed, "
                "will use word-count fallback.",
                int(first_len / total_len * 100),
            )
            return []

    return valid


def segment_module_topics(
    content_item_id: str,
    extracted_text: str,
    module_title: str,
    course_title: str,
) -> dict:
    """Hybrid segmentation: regex fast-path, LLM fallback, then word-count chunks."""
    del content_item_id
    word_count = len(extracted_text.split())
    script = _detect_script(extracted_text)

    topics: List[dict] = []
    method = "regex"

    if script == "latin":
        topics = _regex_segment_topics(extracted_text)

    if len(topics) < 2 and word_count > 250:
        llm_topics = _llm_segment_topics(extracted_text, module_title, course_title)
        if len(llm_topics) >= 2:
            topics = llm_topics
            method = "llm"

    if len(topics) < 2 and word_count > 250:
        words = extracted_text.split()
        chunk_size = 500
        topics = [
            {
                "title": f"Section {i // chunk_size + 1}",
                "content": " ".join(words[i : i + chunk_size]),
            }
            for i in range(0, len(words), chunk_size)
        ]
        method = "wordcount_fallback"

    if not topics and extracted_text.strip():
        topics = [{"title": module_title, "content": extracted_text.strip()}]
        method = "single_block_fallback"

    return {
        "topics": topics,
        "method": method,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def save_topics(content_item_id: str, payload: dict, db: Optional[Session] = None) -> None:
    """
    Saves topic segmentation to PostgreSQL (ContentItem.topics_json).
    Also writes to disk as a fast local cache for the current deployment.
    """
    serialized = json.dumps(payload, ensure_ascii=False)

    try:
        path = _topics_json_path(content_item_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding="utf-8")
    except Exception as exc:
        logger.warning("[SAVE TOPICS DISK] %s: %s (non-fatal)", content_item_id, exc)

    close_db = False
    if db is None:
        from fastapi_app.database import SessionLocal

        db = SessionLocal()
        close_db = True

    try:
        record = db.get(ContentItem, content_item_id)
        if record:
            record.topics_json = serialized
            db.commit()
    except Exception as exc:
        logger.warning("[SAVE TOPICS DB] %s: %s", content_item_id, exc)
    finally:
        if close_db:
            db.close()


def _parse_and_validate_topics(raw_json: str, extracted_text: str = "") -> Optional[List[dict]]:
    try:
        data = json.loads(raw_json)
        topics = data.get("topics", []) if isinstance(data, dict) else data
        if not isinstance(topics, list) or not topics:
            return None
        if extracted_text:
            word_count = len(extracted_text.split())
            if len(topics) <= 1 and word_count > 400:
                logger.info(
                    "[TOPIC CACHE] cached result has %s topic(s) for %s-word document — invalidated",
                    len(topics),
                    word_count,
                )
                return None
        return topics
    except Exception:
        return None


def load_topics(
    content_item_id: str,
    extracted_text: str = "",
    db: Optional[Session] = None,
) -> Optional[List[dict]]:
    """
    Loads cached topics. Priority:
    1. Local disk (fast, exists within current deployment)
    2. PostgreSQL (survives across deployments)
    Returns None if neither source has valid data (triggers re-segmentation).
    """
    disk_path = _topics_json_path(content_item_id)
    if disk_path.exists():
        try:
            result = _parse_and_validate_topics(disk_path.read_text(encoding="utf-8"), extracted_text)
            if result:
                return result
        except Exception:
            pass

    close_db = False
    if db is None:
        from fastapi_app.database import SessionLocal

        db = SessionLocal()
        close_db = True

    try:
        record = db.get(ContentItem, content_item_id)
        if record and record.topics_json:
            result = _parse_and_validate_topics(record.topics_json, extracted_text)
            if result:
                try:
                    disk_path.parent.mkdir(parents=True, exist_ok=True)
                    disk_path.write_text(record.topics_json, encoding="utf-8")
                except Exception:
                    pass
                return result
    except Exception as exc:
        logger.warning("[LOAD TOPICS DB] %s: %s", content_item_id, exc)
    finally:
        if close_db:
            db.close()

    return None


def _faiss_index_path(content_item_id: str) -> Path:
    return MODULE_EMBEDDINGS_DIR / content_item_id / f"{content_item_id}.faiss"


def _rebuild_faiss_from_text(content_item_id: str, extracted_text: str) -> None:
    """
    Rebuilds FAISS index from already-extracted text.
    Used after a deployment clears the ephemeral disk.
    Does NOT re-call pypdf — uses text already stored in PostgreSQL.
    """
    if not extracted_text.strip():
        return
    embed_content_item(content_item_id, extracted_text)
    logger.info(
        "[REBUILD] %s: FAISS rebuilt from stored extracted_text",
        content_item_id,
    )


def _segment_and_cache_topics(
    content_item_id: str,
    extracted_text: str,
    module_title: str,
    course_title: str,
    db: Optional[Session] = None,
) -> None:
    payload = segment_module_topics(
        content_item_id=content_item_id,
        extracted_text=extracted_text,
        module_title=module_title,
        course_title=course_title,
    )
    save_topics(content_item_id, payload, db=db)
    logger.info(
        "module_topics_segmented",
        extra={
            "content_item_id": content_item_id,
            "topic_count": len(payload.get("topics", [])),
            "method": payload.get("method"),
        },
    )



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
        if not _faiss_index_path(content_item_id).exists() and item.extracted_text:
            _rebuild_faiss_from_text(content_item_id, item.extracted_text)
    store = ModuleContentVectorStore(content_item_id)
    return store.search(query, top_k=top_k)


def _resolve_file_path(content_item: ContentItem) -> Optional[str]:
    from fastapi_app.services import upload_service

    item_id = content_item.item_id
    if item_id.startswith("upload_"):
        upload_id = item_id.replace("upload_", "", 1)
        record = upload_service.get_material(upload_id)
        if record:
            return upload_service.resolve_material_file_path(record)
    payload = dict(content_item.payload_json or {})
    local = payload.get("file_path")
    if local and Path(local).exists():
        return local
    r2_key = payload.get("r2_key")
    if r2_key:
        return upload_service.resolve_r2_key_to_local(r2_key, item_id)
    return local


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
    extracted = ""
    module_title = ""
    course_title = ""
    with db._SessionLocal() as session:  # noqa: SLF001
        item = session.get(ContentItem, content_item_id)
        if item is None:
            return
        source_type = (item.source_type or "").lower()
        if source_type not in PDF_SOURCE_TYPES:
            item.embedding_status = "skipped"
            session.commit()
            return

        if item.extracted_text and (item.embedding_status or "") == "embedded":
            if _faiss_index_path(content_item_id).exists():
                return
            _rebuild_faiss_from_text(content_item_id, item.extracted_text)
            return

        file_path = _resolve_file_path(item)
        if file_path and Path(file_path).exists():
            extracted = extract_pdf_text(file_path)
        elif item.extracted_text:
            extracted = item.extracted_text
        else:
            item.embedding_status = "failed"
            session.commit()
            return

        module_title = item.title or ""
        if item.course_id:
            from fastapi_app.admin.models import Course

            course = session.get(Course, item.course_id)
            if course:
                course_title = course.course_title or ""

        item.extracted_text = extracted or None
        item.embedding_status = "pending"
        session.commit()

    if extracted:
        embed_content_item(content_item_id, extracted)
        try:
            with db._SessionLocal() as session:  # noqa: SLF001
                _segment_and_cache_topics(
                    content_item_id,
                    extracted,
                    module_title,
                    course_title,
                    db=session,
                )
        except Exception:
            logger.exception(
                "module_topic_segmentation_failed",
                extra={"content_item_id": content_item_id},
            )
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
