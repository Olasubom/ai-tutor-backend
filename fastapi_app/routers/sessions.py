from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from fastapi_app.security import require_api_key
from fastapi_app.services import sessions_service

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("/{learner_id}")
def list_sessions(learner_id: str, _: None = Depends(require_api_key)):
    return sessions_service.list_sessions(learner_id)


@router.get("/{learner_id}/{session_id}/messages")
def session_messages(learner_id: str, session_id: str, _: None = Depends(require_api_key)):
    messages = sessions_service.get_session_messages(learner_id, session_id)
    if not messages:
        sessions = sessions_service.list_sessions(learner_id)
        if not any(s.get("session_id") == session_id for s in sessions):
            raise HTTPException(status_code=404, detail={"detail": "Session not found", "code": "not_found"})
    return messages
