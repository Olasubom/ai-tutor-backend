"""File-based memory store at project /memory (per platform spec)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, List, Optional

_ROOT = Path(__file__).resolve().parents[2]
MEMORY_ROOT = _ROOT / "memory"

MEMORY_DIRS = [
    "quizzes",
    "sessions",
    "chat",
    "notifications",
    "goals",
    "spaced_rep",
    "events",
    "lecturers",
    "at_risk_dismissed",
    "onboarding",
    "engagement",
    "rosters",
    "courses",
    "auth",
    "structured",
]


def ensure_memory_dirs() -> None:
    for name in MEMORY_DIRS:
        (MEMORY_ROOT / name).mkdir(parents=True, exist_ok=True)


def _path(*parts: str) -> Path:
    return MEMORY_ROOT.joinpath(*parts)


def read_json(rel_path: str, default: Any) -> Any:
    path = _path(rel_path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def write_json(rel_path: str, data: Any) -> None:
    path = _path(rel_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def append_jsonl(rel_path: str, record: dict) -> None:
    path = _path(rel_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def read_jsonl(rel_path: str) -> List[dict]:
    path = _path(rel_path)
    if not path.exists():
        return []
    rows: List[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def cap_list(items: list, max_size: int) -> list:
    if len(items) <= max_size:
        return items
    return items[-max_size:]
