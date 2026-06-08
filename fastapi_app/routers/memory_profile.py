from __future__ import annotations

from fastapi import APIRouter, Depends

from fastapi_app.security import require_api_key
from fastapi_app.services import memory_profile_service

router = APIRouter(prefix="/memory-profile", tags=["Memory Profile"])


@router.get("/{learner_id}")
def get_memory_profile(learner_id: str, _: None = Depends(require_api_key)):
    return memory_profile_service.get_memory_profile(learner_id)
