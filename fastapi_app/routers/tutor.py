"""
AI Tutor API routes.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from agency.tutor_service import (
    backfill_content_source_origin,
    get_db_health_snapshot,
    get_learner_profile_snapshot,
    handle_recommend_request,
    handle_tutor_request,
    ingest_source_items,
    list_ingestion_history_snapshot,
    list_content_items_snapshot,
    reset_learner_state,
)
from fastapi_app.schemas.learner import (
    BackfillSourceOriginResponse,
    ContentItemsResponse,
    IngestSourcesRequest,
    IngestSourcesResponse,
    IngestionHistoryResponse,
    LearnerProfileResponse,
    TutorChatRequest,
    TutorChatResponse,
    TutorRecommendRequest,
    TutorRecommendResponse,
)
from fastapi_app.schemas.platform import KnowledgePatchRequest, KnowledgeSeedRequest
from fastapi_app.security import require_api_key, require_dev_token
from fastapi_app.services import knowledge_service, onboarding_service, sessions_service
from fastapi_app.services.engagement_service import record_engagement

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tutor", tags=["AI Tutor"])


@router.post("/chat", response_model=TutorChatResponse)
def tutor_chat(payload: TutorChatRequest, _: None = Depends(require_api_key)) -> TutorChatResponse:
    """Full multi-agent tutoring chat via CoordinatorAgent."""
    try:
        events = [e.model_dump() for e in payload.events] if payload.events else None
        session_id = payload.session_id
        subject = (payload.course_context or {}).get("subject", "General")
        session = sessions_service.get_or_create_session(
            payload.learner_id, session_id=session_id, subject=str(subject)
        )
        result = handle_tutor_request(
            learner_id=payload.learner_id,
            message=payload.message,
            course_context=payload.course_context,
            events=events,
            time_budget_minutes=payload.time_budget_minutes,
        )
        topic = str(subject) if subject != "General" else None
        sessions_service.touch_session(
            payload.learner_id,
            session["session_id"],
            user_message=payload.message,
            assistant_message=result["assistant_message"],
            topic=topic,
        )
        record_engagement(payload.learner_id, "chat_message", {"session_id": session["session_id"]})
        result["session_id"] = session["session_id"]
        return TutorChatResponse(**result)
    except Exception as exc:
        logger.exception("tutor_chat_failed", extra={"learner_id": payload.learner_id})
        raise HTTPException(status_code=500, detail={"detail": str(exc), "code": "chat_error"}) from exc


@router.post("/recommend", response_model=TutorRecommendResponse)
def tutor_recommend(
    payload: TutorRecommendRequest,
    _: None = Depends(require_api_key),
) -> TutorRecommendResponse:
    """
    Direct recommendations without full Coordinator orchestration.

    Uses deterministic hybrid ranking by default (no OpenAI required).
    """
    try:
        events = [e.model_dump() for e in payload.events] if payload.events else None
        result = handle_recommend_request(
            learner_id=payload.learner_id,
            message=payload.message,
            course_context=payload.course_context,
            events=events,
            limit=payload.limit,
            use_agent=payload.use_agent,
        )
        return TutorRecommendResponse(
            request_id=result["request_id"],
            learner_id=result["learner_id"],
            source=result["source"],
            recommendations=result.get("recommendations", []),
            adaptive_path=result.get("adaptive_path", []),
            memory_used=result.get("memory_used"),
            timestamp=result["timestamp"],
        )
    except Exception as exc:
        logger.exception("tutor_recommend_failed", extra={"learner_id": payload.learner_id})
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ai-tutor-backend"}


@router.get("/profile/{learner_id}", response_model=LearnerProfileResponse)
def learner_profile(
    learner_id: str,
    _: None = Depends(require_api_key),
) -> LearnerProfileResponse:
    """Debug endpoint to inspect per-learner personalization state."""
    try:
        result = get_learner_profile_snapshot(learner_id)
        result["profile"] = knowledge_service.enrich_profile(learner_id, result["profile"])
        return LearnerProfileResponse(**result)
    except Exception as exc:
        logger.exception("learner_profile_failed", extra={"learner_id": learner_id})
        raise HTTPException(status_code=500, detail={"detail": str(exc), "code": "profile_error"}) from exc


@router.get("/knowledge/{learner_id}")
def learner_knowledge(learner_id: str, _: None = Depends(require_api_key)):
    return knowledge_service.get_knowledge(learner_id)


@router.get("/knowledge/trajectory/{learner_id}")
def knowledge_trajectory(learner_id: str, _: None = Depends(require_api_key)):
    return knowledge_service.mastery_trajectory(learner_id)


@router.patch("/knowledge/{learner_id}/{topic}")
def patch_knowledge(
    learner_id: str, topic: str, payload: KnowledgePatchRequest, _: None = Depends(require_api_key)
):
    return knowledge_service.patch_topic(learner_id, topic, payload.proficiency)


@router.post("/knowledge/seed")
def seed_knowledge(payload: KnowledgeSeedRequest, _: None = Depends(require_api_key)):
    return onboarding_service.seed_knowledge(payload.learner_id, payload.assessments)


@router.get("/db-health")
def db_health(
    _: None = Depends(require_dev_token),
) -> dict:
    """Debug endpoint for DB table presence and row counts."""
    try:
        return get_db_health_snapshot()
    except Exception as exc:
        logger.exception("db_health_failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/reset-learner/{learner_id}")
def reset_learner(
    learner_id: str,
    _: None = Depends(require_dev_token),
) -> dict:
    """Dev-only route to reset one learner's persisted state."""
    try:
        return reset_learner_state(learner_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("reset_learner_failed", extra={"learner_id": learner_id})
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/ingest-sources", response_model=IngestSourcesResponse)
def ingest_sources(
    payload: IngestSourcesRequest,
    _: None = Depends(require_dev_token),
) -> IngestSourcesResponse:
    """Dev-only route to ingest external content sources into content_items."""
    try:
        result = ingest_source_items(
            source=payload.source,
            topics=payload.topics,
            max_per_topic=payload.max_per_topic,
        )
        return IngestSourcesResponse(**result)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("ingest_sources_failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/content-items", response_model=ContentItemsResponse)
def content_items(
    topic: str | None = None,
    modality: str | None = None,
    source_type: str | None = None,
    source_origin: str | None = None,
    limit: int = 100,
    _: None = Depends(require_dev_token),
) -> ContentItemsResponse:
    """Dev-only route to inspect DB-backed content catalog with filters."""
    try:
        result = list_content_items_snapshot(
            topic=topic,
            modality=modality,
            source_type=source_type,
            source_origin=source_origin,
            limit=max(1, min(limit, 500)),
        )
        return ContentItemsResponse(**result)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("content_items_failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/backfill-source-origin", response_model=BackfillSourceOriginResponse)
def backfill_source_origin(
    _: None = Depends(require_dev_token),
) -> BackfillSourceOriginResponse:
    """Dev-only route to backfill source_origin on legacy content_items."""
    try:
        result = backfill_content_source_origin()
        return BackfillSourceOriginResponse(**result)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("backfill_source_origin_failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/ingestion-history", response_model=IngestionHistoryResponse)
def ingestion_history(
    limit: int = 20,
    _: None = Depends(require_dev_token),
) -> IngestionHistoryResponse:
    """Dev-only route to inspect recent ingestion runs."""
    try:
        result = list_ingestion_history_snapshot(limit=limit)
        return IngestionHistoryResponse(**result)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("ingestion_history_failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
