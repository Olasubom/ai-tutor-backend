from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from agency.core.context import get_runtime
from fastapi_app.services.memory_files import read_json, write_json


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(learner_id: str) -> dict:
    return read_json(f"onboarding/{learner_id}.json", {"completed_steps": [], "data": {}})


def _save(learner_id: str, payload: dict) -> None:
    write_json(f"onboarding/{learner_id}.json", payload)


def get_status(learner_id: str) -> dict:
    data = _load(learner_id)
    steps = data.get("completed_steps", [])
    return {"completed_steps": steps, "is_complete": len(steps) >= 4}


def step1(learner_id: str, body: dict) -> dict:
    data = _load(learner_id)
    data["data"]["step1"] = body
    if 1 not in data["completed_steps"]:
        data["completed_steps"].append(1)
    _save(learner_id, data)
    runtime = get_runtime()
    runtime.learner_memory.upsert_profile(learner_id, {"onboarding": data["data"]})
    return {"ok": True, "completed_steps": data["completed_steps"]}


def step2(learner_id: str, body: dict) -> dict:
    from fastapi_app.auth.memory import update_structured_memory
    from fastapi_app.services.lecturer_service import enroll_student

    data = _load(learner_id)
    data["data"]["step2"] = body
    if 2 not in data["completed_steps"]:
        data["completed_steps"].append(2)
    _save(learner_id, data)
    runtime = get_runtime()
    runtime.learner_memory.upsert_profile(learner_id, {"onboarding": data["data"]})

    selected_ids = body.get("selected_course_ids") or []
    if selected_ids:
        update_structured_memory(learner_id, {"courses": selected_ids})

    step1 = data.get("data", {}).get("step1", {})
    enroll_student(
        learner_id,
        name=step1.get("full_name", learner_id),
        department_id=body.get("department_id", "general"),
        level=body.get("level", "100"),
    )
    return {"ok": True, "completed_steps": data["completed_steps"]}


def step4(learner_id: str, body: dict) -> dict:
    data = _load(learner_id)
    data["data"]["step4"] = body
    if 4 not in data["completed_steps"]:
        data["completed_steps"].append(4)
    _save(learner_id, data)
    runtime = get_runtime()
    runtime.learner_memory.upsert_profile(
        learner_id,
        {"onboarding": data["data"], "preferences": body},
    )
    return {"ok": True, "completed_steps": data["completed_steps"]}


def seed_knowledge(learner_id: str, assessments: List[dict]) -> dict:
    from fastapi_app.services.mastery_seed import seed_topic_mastery_from_assessments

    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(learner_id)
    topic_mastery = dict(profile.get("topic_mastery") or {})
    topic_mastery, summary = seed_topic_mastery_from_assessments(topic_mastery, assessments)
    runtime.learner_memory.upsert_profile(
        learner_id,
        {"topic_mastery": topic_mastery, "knowledge_state_summary": summary},
    )

    data = _load(learner_id)
    data["data"]["step3"] = {"assessments": assessments}
    if 3 not in data["completed_steps"]:
        data["completed_steps"].append(3)
    _save(learner_id, data)
    return {"seeded": len(assessments), "completed_steps": data["completed_steps"]}
