from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from agency.core.context import get_runtime
from fastapi_app.security import require_api_key
from fastapi_app.services.memory_files import read_json, write_json

router = APIRouter(prefix="/auth", tags=["Auth Profile"])


class ProfilePatchRequest(BaseModel):
    learner_id: str
    full_name: Optional[str] = None
    field_of_study: Optional[str] = None
    institution: Optional[str] = None
    department_id: Optional[str] = None
    academic_level: Optional[str] = None


@router.patch("/profile")
def patch_profile(payload: ProfilePatchRequest, _: None = Depends(require_api_key)) -> dict:
    runtime = get_runtime()
    profile = runtime.learner_memory.get_profile(payload.learner_id)
    onboarding = profile.get("onboarding") or read_json(f"onboarding/{payload.learner_id}.json", {}).get("data", {})
    step1 = onboarding.get("step1") or {}
    if payload.full_name is not None:
        step1["full_name"] = payload.full_name
    if payload.field_of_study is not None:
        step1["field_of_study"] = payload.field_of_study
    if payload.institution is not None:
        step1["institution"] = payload.institution
    if payload.academic_level is not None:
        step1["proficiency_level"] = payload.academic_level
    onboarding["step1"] = step1
    if payload.department_id is not None:
        step2 = onboarding.get("step2") or {}
        step2["department_id"] = payload.department_id
        onboarding["step2"] = step2
    runtime.learner_memory.upsert_profile(payload.learner_id, {"onboarding": onboarding})
    data = read_json(f"onboarding/{payload.learner_id}.json", {"completed_steps": [], "data": {}})
    data["data"] = onboarding
    write_json(f"onboarding/{payload.learner_id}.json", data)
    return {"ok": True, "profile": onboarding}
