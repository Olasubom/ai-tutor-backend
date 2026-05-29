from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def safe_div(n: float, d: float, default: float = 0.0) -> float:
    return n / d if d else default


@dataclass(frozen=True)
class RankedItem:
    item_id: str
    score: float
    reasons: List[str]
    payload: Dict[str, Any]

