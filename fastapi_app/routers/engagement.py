from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from fastapi_app.schemas.platform import EngagementRequest
from fastapi_app.security import require_api_key
from fastapi_app.services import engagement_service

router = APIRouter(prefix="/engagement", tags=["Engagement"])


@router.post("/{learner_id}")
def record_engagement(learner_id: str, payload: EngagementRequest, _: None = Depends(require_api_key)):
    return engagement_service.record_engagement(learner_id, payload.event_type, payload.metadata)


@router.get("/{learner_id}/heatmap")
def heatmap(
    learner_id: str,
    period: str = Query(default="all", pattern="^(7d|30d|all)$"),
    _: None = Depends(require_api_key),
):
    return engagement_service.get_heatmap(learner_id, period)


@router.get("/{learner_id}")
def engagement_metrics(
    learner_id: str,
    period: str = Query(default="7d", pattern="^(7d|30d|all)$"),
    _: None = Depends(require_api_key),
):
    return engagement_service.get_daily_metrics(learner_id, period)
