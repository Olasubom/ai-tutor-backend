from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from agency.core.tools.utils import RankedItem, clamp, safe_div


def hybrid_recommend(
    *,
    catalog: List[Dict[str, Any]],
    weak_topics: List[str],
    preferences: List[str],
    memory_snippets: List[str],
    preferred_modalities: Optional[List[str]] = None,
    limit: int = 6,
) -> Tuple[List[RankedItem], List[Dict[str, Any]]]:
    if not catalog:
        return [], []

    max_pop = max((float(item.get("popularity_score", 0.0)) for item in catalog), default=1.0) or 1.0
    weak_set = {t.lower() for t in weak_topics}
    pref_text = " ".join(preferences).lower()
    memory_text = " ".join(memory_snippets).lower()
    preferred_modalities = [m.strip().lower() for m in (preferred_modalities or []) if m]
    preferred_modalities_set = set(preferred_modalities)

    ranked: List[RankedItem] = []
    for item in catalog:
        # Support both legacy and improved catalog schemas.
        topics = [t.lower() for t in item.get("topics", [])]
        tags = [t.lower() for t in item.get("tags", [])]
        if not topics:
            topics = tags
        topic_label = str(item.get("topic", "")).lower().strip()
        if topic_label and topic_label not in topics:
            topics.append(topic_label)
        modality = str(item.get("modality", "")).lower().strip()
        bloom_level = str(item.get("bloom_level", "")).lower().strip()
        reasons: List[str] = []

        content_score = 0.0
        if weak_set and any(any(weak in t or t in weak for weak in weak_set) for t in topics):
            content_score = 1.0
            reasons.append("targets weak topic")
        elif not weak_set:
            content_score = 0.5
            reasons.append("general progression")

        collab_score = safe_div(float(item.get("popularity_score", 0.0)), max_pop)
        if collab_score >= 0.7:
            reasons.append("popular with similar learners")

        memory_score = 0.0
        title = str(item.get("title", "")).lower()
        if any(tag in memory_text or tag in pref_text for tag in topics):
            memory_score = 0.8
            reasons.append("matches learner preferences/memory")
        if title and title in memory_text:
            memory_score = max(memory_score, 0.9)
            reasons.append("aligned with past interests")

        modality_score = 0.0
        if preferred_modalities_set and modality in preferred_modalities_set:
            modality_score = 1.0
            reasons.append(f"matches preferred modality: {modality}")
        elif preferred_modalities_set:
            modality_score = 0.1
        elif modality:
            modality_score = 0.4
            reasons.append("supports balanced modality mix")

        bloom_score = 0.5
        if weak_set:
            if bloom_level in {"remember", "understand", "apply"}:
                bloom_score = 0.9
                reasons.append(f"appropriate Bloom level: {bloom_level}")
            elif bloom_level:
                bloom_score = 0.35
        else:
            if bloom_level in {"apply", "analyze", "evaluate", "create"}:
                bloom_score = 0.75
                reasons.append(f"advances Bloom level: {bloom_level}")

        score = clamp(
            0.32 * content_score
            + 0.12 * collab_score
            + 0.18 * memory_score
            + 0.28 * modality_score
            + 0.10 * bloom_score
        )
        ranked.append(
            RankedItem(
                item_id=str(item["id"]),
                score=score,
                reasons=reasons or ["recommended next step"],
                payload=item,
            )
        )

    ranked.sort(key=lambda r: r.score, reverse=True)
    top = ranked[:limit]
    adaptive_path = [
        {
            "step": idx + 1,
            "item_id": r.item_id,
            "title": r.payload.get("title"),
            "objective": r.payload.get("objective", "Study and practice"),
            "estimated_minutes": r.payload.get("duration_minutes", 30),
            "modality": r.payload.get("modality"),
            "bloom_level": r.payload.get("bloom_level"),
        }
        for idx, r in enumerate(top[:5])
    ]
    return top, adaptive_path
