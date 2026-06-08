from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from fastapi_app.schemas.platform import GoalCreateRequest
from fastapi_app.security import require_api_key
from fastapi_app.services import goals_service

router = APIRouter(prefix="/goals", tags=["Goals"])


@router.get("/{learner_id}")
def list_goals(learner_id: str, _: None = Depends(require_api_key)):
    return goals_service.list_goals(learner_id)


@router.post("/{learner_id}")
def create_goal(learner_id: str, payload: GoalCreateRequest, _: None = Depends(require_api_key)):
    return goals_service.create_goal(
        learner_id, payload.topic, payload.target_mastery, payload.target_date
    )


@router.delete("/{learner_id}/{goal_id}")
def delete_goal(learner_id: str, goal_id: str, _: None = Depends(require_api_key)):
    ok = goals_service.delete_goal(learner_id, goal_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"detail": "Goal not found", "code": "not_found"})
    return {"ok": True}
