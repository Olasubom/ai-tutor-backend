"""Per-learner module progress within a course curriculum."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.core.tools.models import ContentItem, ModuleProgress


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _item_description(item: ContentItem) -> str:
    payload = dict(item.payload_json or {})
    return str(payload.get("description") or "")


def get_progress_map(db: Session, learner_id: str, item_ids: List[str]) -> Dict[str, ModuleProgress]:
    if not item_ids:
        return {}
    rows = db.scalars(
        select(ModuleProgress).where(
            ModuleProgress.learner_id == learner_id,
            ModuleProgress.content_item_id.in_(item_ids),
        )
    ).all()
    return {row.content_item_id: row for row in rows}


def build_modules_from_items(
    items: List[ContentItem],
    learner_id: str,
    db: Session,
) -> List[Dict[str, Any]]:
    """Build curriculum modules with per-item progress and sequential locking."""
    item_ids = [item.item_id for item in items]
    progress_map = get_progress_map(db, learner_id, item_ids)
    modules: List[Dict[str, Any]] = []

    for idx, item in enumerate(items):
        progress = progress_map.get(item.item_id)
        percent = int(progress.percent_complete) if progress else 0
        status_val = progress.status if progress else "not_started"

        if idx == 0:
            if status_val == "not_started":
                status_val = "in_progress"
        else:
            prev = progress_map.get(items[idx - 1].item_id)
            prev_status = prev.status if prev else "not_started"
            if prev_status != "completed":
                status_val = "locked"

        modules.append(
            {
                "module_number": idx + 1,
                "step": idx + 1,
                "content_item_id": item.item_id,
                "item_id": item.item_id,
                "title": item.title,
                "description": _item_description(item),
                "objective": _item_description(item) or "Study and practice",
                "source_type": item.source_type,
                "source_url": item.source_url,
                "modality": item.modality,
                "module_type": "core",
                "status": status_val,
                "percent_complete": percent,
            }
        )

    return modules


def upsert_module_progress(
    db: Session,
    *,
    learner_id: str,
    content_item_id: str,
    percent_complete: int,
    status: str,
) -> ModuleProgress:
    row = db.scalars(
        select(ModuleProgress).where(
            ModuleProgress.learner_id == learner_id,
            ModuleProgress.content_item_id == content_item_id,
        )
    ).first()
    if row is None:
        row = ModuleProgress(learner_id=learner_id, content_item_id=content_item_id)
        db.add(row)

    row.percent_complete = max(0, min(100, int(percent_complete)))
    row.status = status
    row.last_updated = _now()
    db.commit()
    db.refresh(row)
    return row
