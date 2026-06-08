from __future__ import annotations

from fastapi import APIRouter, Depends

from fastapi_app.schemas.platform import (
    KnowledgeSeedRequest,
    OnboardingStep1,
    OnboardingStep2,
    OnboardingStep4,
)
from fastapi_app.security import require_api_key
from fastapi_app.services import onboarding_service

router = APIRouter(prefix="/auth/onboarding", tags=["Onboarding"])


@router.get("/status/{learner_id}")
def onboarding_status(learner_id: str, _: None = Depends(require_api_key)):
    return onboarding_service.get_status(learner_id)


@router.post("/step1")
def step1(payload: OnboardingStep1, _: None = Depends(require_api_key)):
    return onboarding_service.step1(
        payload.learner_id,
        payload.model_dump(exclude={"learner_id"}),
    )


@router.post("/step2")
def step2(payload: OnboardingStep2, _: None = Depends(require_api_key)):
    return onboarding_service.step2(
        payload.learner_id,
        payload.model_dump(exclude={"learner_id"}),
    )


@router.post("/step4")
def step4(payload: OnboardingStep4, _: None = Depends(require_api_key)):
    return onboarding_service.step4(
        payload.learner_id,
        payload.model_dump(exclude={"learner_id"}),
    )
