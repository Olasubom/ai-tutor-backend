from __future__ import annotations

from fastapi import APIRouter, Depends

from fastapi_app.security import require_api_key
from fastapi_app.services import at_risk_service

router = APIRouter(prefix="/at-risk", tags=["At Risk"])


@router.get("/{lecturer_id}")
def list_at_risk(lecturer_id: str, _: None = Depends(require_api_key)):
    return at_risk_service.list_at_risk(lecturer_id)


@router.patch("/{lecturer_id}/{learner_id}/dismiss")
def dismiss_alert(lecturer_id: str, learner_id: str, _: None = Depends(require_api_key)):
    at_risk_service.dismiss_alert(lecturer_id, learner_id)
    return {"ok": True}
