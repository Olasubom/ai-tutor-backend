"""Uploaded learning material metadata and ingestion."""

from __future__ import annotations

import logging
import mimetypes
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from agency.core.tools.database import Database
from agency.core.tools.models import ContentItem
from fastapi_app.services.memory_files import read_json, write_json

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(_ROOT / "uploads" / "materials")))
MAX_FILE_SIZE_MB = float(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
METADATA_PATH = "uploads/materials.json"

ALLOWED_MIME_TYPES = {
    "application/pdf": "pdf",
    "video/mp4": "video",
    "video/webm": "video",
    "audio/mpeg": "audio",
    "audio/mp4": "audio",
    "text/plain": "text",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
    "application/msword": "document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "slides",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_materials() -> List[dict]:
    data = read_json(METADATA_PATH, [])
    return data if isinstance(data, list) else []


def _save_materials(materials: List[dict]) -> None:
    write_json(METADATA_PATH, materials)


def _public_record(record: dict) -> dict:
    return {k: v for k, v in record.items() if k != "file_path"}


def resolve_content_type(filename: str, content_type: Optional[str]) -> str:
    guessed = content_type or mimetypes.guess_type(filename)[0] or ""
    return guessed.split(";")[0].strip().lower()


def validate_upload(content_type: str, size_bytes: int) -> tuple[str, float]:
    if content_type not in ALLOWED_MIME_TYPES:
        raise ValueError(
            f"File type not allowed: {content_type or 'unknown'}. "
            "Allowed: PDF, MP4, WebM, MP3, DOCX, PPTX, TXT"
        )
    size_mb = size_bytes / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"File too large: {size_mb:.1f}MB. Maximum: {MAX_FILE_SIZE_MB:.0f}MB")
    return ALLOWED_MIME_TYPES[content_type], size_mb


def save_material_file(contents: bytes, filename: str) -> tuple[str, str, str]:
    upload_id = str(uuid.uuid4())
    upload_path = UPLOAD_DIR / upload_id
    upload_path.mkdir(parents=True, exist_ok=True)
    safe_filename = f"{upload_id}_{Path(filename).name}"
    file_path = upload_path / safe_filename
    file_path.write_bytes(contents)
    return upload_id, str(file_path), safe_filename


def create_material_record(
    *,
    upload_id: str,
    safe_filename: str,
    original_name: str,
    file_type: str,
    size_mb: float,
    title: str,
    description: Optional[str],
    course_id: str,
    course_code: str,
    course_title: str,
    module_order: Optional[int],
    uploaded_by: str,
    uploaded_by_name: str,
    college: Optional[str],
    department: Optional[str],
    status: str,
    file_path: str,
) -> dict:
    return {
        "id": upload_id,
        "filename": safe_filename,
        "original_name": original_name,
        "file_type": file_type,
        "file_size_mb": round(size_mb, 2),
        "title": title,
        "description": description,
        "course_id": course_id,
        "course_code": course_code,
        "course_title": course_title,
        "module_order": module_order,
        "uploaded_by": uploaded_by,
        "uploaded_by_name": uploaded_by_name,
        "college": college,
        "department": department,
        "status": status,
        "created_at": _now(),
        "file_path": file_path,
        "url": f"/upload/material/{upload_id}/download",
    }


def sync_content_item(record: dict) -> None:
    """Upsert a ContentItem row linked directly to the upload's course."""
    try:
        from agency.core.context import get_runtime

        runtime = get_runtime()
        if runtime.repository is None:
            logger.warning("sync_content_item_skipped_no_repository", extra={"upload_id": record.get("id")})
            return

        modality_map = {
            "pdf": "text",
            "video": "video",
            "audio": "read_aloud",
            "text": "text",
            "document": "text",
            "slides": "text",
        }
        item_id = f"upload_{record['id']}"
        runtime.repository.upsert_content_items(
            [
                {
                    "id": item_id,
                    "title": record["title"],
                    "topic": record.get("course_title") or "general",
                    "description": record.get("description") or "",
                    "modality": modality_map.get(record.get("file_type", ""), "text"),
                    "source_type": record.get("file_type"),
                    "provider": record.get("uploaded_by_name") or "lecturer",
                    "source_url": record.get("url") or "",
                    "source_origin": "lecturer_upload",
                    "course_id": record.get("course_id"),
                    "course_code": record.get("course_code"),
                    "course_title": record.get("course_title"),
                    "module_order": record.get("module_order"),
                    "status": record.get("status") or "pending_review",
                    "uploaded_by": record.get("uploaded_by"),
                    "department": record.get("department"),
                }
            ]
        )
        runtime.catalog = runtime.repository.list_content_items(limit=5000) or runtime.catalog
        logger.info("sync_content_item_ok", extra={"upload_id": record.get("id"), "item_id": item_id})
    except Exception:
        logger.exception("sync_content_item_failed", extra={"upload_id": record.get("id")})


def update_content_item_status(upload_id: str, status: str) -> None:
    """Update review status on the linked ContentItem after admin approval."""
    try:
        from agency.core.context import get_runtime

        db = Database()
        item_id = f"upload_{upload_id}"
        with db._SessionLocal() as session:  # noqa: SLF001
            row = session.get(ContentItem, item_id)
            if row is None:
                return
            row.status = status
            session.commit()

        runtime = get_runtime()
        if runtime.repository is not None:
            runtime.catalog = runtime.repository.list_content_items(limit=5000) or runtime.catalog
    except Exception:
        logger.exception("update_content_item_status_failed", extra={"upload_id": upload_id})


def append_material(record: dict) -> dict:
    materials = _load_materials()
    materials.append(record)
    _save_materials(materials)
    sync_content_item(record)
    return record


def get_material(upload_id: str) -> Optional[dict]:
    return next((m for m in _load_materials() if m.get("id") == upload_id), None)


def list_materials_for_user(
    *,
    role: str,
    user_id: str,
    status: Optional[str] = None,
    department: Optional[str] = None,
    subject: Optional[str] = None,
    uploader_id: Optional[str] = None,
) -> List[dict]:
    materials = _load_materials()

    if role == "student":
        materials = [m for m in materials if m.get("status") == "approved"]
    elif role == "lecturer":
        materials = [
            m for m in materials if m.get("status") == "approved" or m.get("uploaded_by") == user_id
        ]

    if uploader_id:
        materials = [m for m in materials if m.get("uploaded_by") == uploader_id]
    if status:
        materials = [m for m in materials if m.get("status") == status]
    if department:
        materials = [m for m in materials if m.get("department") == department]
    if subject:
        materials = [m for m in materials if m.get("subject") == subject]

    return [_public_record(m) for m in materials]


def update_material(upload_id: str, patch: dict) -> Optional[dict]:
    materials = _load_materials()
    updated = None
    for i, material in enumerate(materials):
        if material.get("id") == upload_id:
            materials[i] = {**material, **patch}
            updated = materials[i]
            break
    if updated is None:
        return None
    _save_materials(materials)
    if "status" in patch:
        update_content_item_status(upload_id, str(patch["status"]))
    return updated


def delete_material(upload_id: str) -> bool:
    materials = _load_materials()
    record = next((m for m in materials if m.get("id") == upload_id), None)
    if not record:
        return False

    upload_dir = UPLOAD_DIR / upload_id
    if upload_dir.exists():
        shutil.rmtree(upload_dir, ignore_errors=True)

    _save_materials([m for m in materials if m.get("id") != upload_id])

    try:
        db = Database()
        with db._SessionLocal() as session:  # noqa: SLF001
            row = session.get(ContentItem, f"upload_{upload_id}")
            if row:
                session.delete(row)
                session.commit()
    except Exception:
        logger.exception("delete_content_item_failed", extra={"upload_id": upload_id})

    return True


def ingest_uploaded_material(record: dict) -> None:
    """Ensure approved upload is synced to content_items and process PDF embeddings."""
    sync_content_item(record)
    if record.get("status") != "approved":
        return
    file_type = (record.get("file_type") or "").lower()
    if file_type in {"pdf", "document"}:
        from fastapi_app.services.module_embedding_service import process_content_item_embeddings

        process_content_item_embeddings(f"upload_{record['id']}")
