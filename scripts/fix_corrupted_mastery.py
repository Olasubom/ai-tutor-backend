"""
Reset topic mastery corrupted to ~100% by the course-events / recommend BKT bug.

Run once: python scripts/fix_corrupted_mastery.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / "agency" / ".env", override=True)

from agency.core.services.bkt import default_skill_state, summarize_mastery  # noqa: E402
from fastapi_app.services.mastery_seed import PROFICIENCY_P_L  # noqa: E402
from fastapi_app.services.memory_files import MEMORY_ROOT, read_json  # noqa: E402

CORRUPT_THRESHOLD = 0.99
DEFAULT_P_L = 0.35


def _load_assessments(learner_id: str) -> List[dict]:
    structured = read_json(f"structured/{learner_id}.json", {})
    ratings = structured.get("subject_ratings")
    if isinstance(ratings, list) and ratings:
        return [r for r in ratings if isinstance(r, dict)]

    onboarding = read_json(f"onboarding/{learner_id}.json", {})
    step3 = (onboarding.get("data") or {}).get("step3") or {}
    assessments = step3.get("assessments")
    if isinstance(assessments, list) and assessments:
        return [a for a in assessments if isinstance(a, dict)]
    return []


def _target_p_l(topic: str, assessments: List[dict]) -> float:
    for assessment in assessments:
        if str(assessment.get("topic") or "").strip() == topic:
            prof = str(assessment.get("proficiency") or "familiar").lower()
            return PROFICIENCY_P_L.get(prof, DEFAULT_P_L)
    return DEFAULT_P_L


def _has_real_quiz_attempts(learner_id: str, topic: str) -> bool:
    events_path = MEMORY_ROOT / "events" / f"{learner_id}.jsonl"
    if not events_path.exists():
        return False
    for line in events_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event_type") != "quiz_submit":
            continue
        event_topic = str(event.get("topic") or event.get("subject") or "").strip()
        if not event_topic or event_topic == topic:
            return True
    return False


def _fix_topic_mastery(
    learner_id: str,
    topic_mastery: Dict[str, Any],
    assessments: List[dict],
) -> bool:
    changed = False
    for topic, state in list(topic_mastery.items()):
        if not isinstance(state, dict):
            continue
        p_l = float(state.get("p_l", 0))
        if p_l < CORRUPT_THRESHOLD:
            continue
        if _has_real_quiz_attempts(learner_id, str(topic)):
            continue

        new_p_l = _target_p_l(str(topic), assessments)
        state["p_l"] = new_p_l
        state["attempts"] = 0
        state["correct_count"] = 0
        state.pop("last_updated", None)
        topic_mastery[topic] = state
        changed = True
        print(f"  reset '{topic}': {p_l:.2f} -> {new_p_l:.2f}")

    return changed


def _recalc_summary(topic_mastery: Dict[str, Any]) -> Dict[str, Any]:
    summary = summarize_mastery(topic_mastery)
    values = [float(s.get("p_l", 0)) for s in topic_mastery.values() if isinstance(s, dict)]
    summary["overall_mastery_percentage"] = round(sum(values) / len(values) * 100) if values else 0
    return summary


def fix_db_profiles() -> int:
    try:
        from sqlalchemy import select

        from agency.core.tools.database import Database
        from agency.core.tools.models import Learner
        from agency.core.tools.repository import LearnerRepository
    except ImportError as exc:
        print(f"Skipping DB profiles: {exc}")
        return 0

    try:
        repo = LearnerRepository(Database())
    except Exception as exc:
        print(f"Skipping DB profiles: {exc}")
        return 0

    fixed = 0
    try:
        with repo._session() as session:  # noqa: SLF001
            learners = session.scalars(select(Learner)).all()
            for learner in learners:
                profile = dict(learner.profile_json or {})
                topic_mastery = profile.get("topic_mastery")
                if not isinstance(topic_mastery, dict) or not topic_mastery:
                    continue

                assessments = _load_assessments(learner.learner_id)
                if not _fix_topic_mastery(learner.learner_id, topic_mastery, assessments):
                    continue

                profile["topic_mastery"] = topic_mastery
                profile["knowledge_state_summary"] = _recalc_summary(topic_mastery)
                repo.upsert_profile(learner.learner_id, profile)
                print(f"Fixed DB learner: {learner.learner_id}")
                fixed += 1
    except Exception as exc:
        print(f"DB scan error: {exc}")

    return fixed


def fix_structured_files() -> int:
    structured_dir = MEMORY_ROOT / "structured"
    if not structured_dir.exists():
        return 0

    fixed = 0
    for path in structured_dir.glob("*.json"):
        learner_id = path.stem
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        topic_mastery = data.get("topic_mastery")
        if not isinstance(topic_mastery, dict) or not topic_mastery:
            continue

        assessments = _load_assessments(learner_id)
        if not _fix_topic_mastery(learner_id, topic_mastery, assessments):
            continue

        data["topic_mastery"] = topic_mastery
        data["knowledge_state_summary"] = _recalc_summary(topic_mastery)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Fixed structured memory: {path.name}")
        fixed += 1

    return fixed


def main() -> None:
    db_fixed = fix_db_profiles()
    file_fixed = fix_structured_files()
    print(f"Done. Fixed {db_fixed} DB profile(s), {file_fixed} structured file(s).")


if __name__ == "__main__":
    main()
