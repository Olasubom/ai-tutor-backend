"""
AI Tutor API routes.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from agency.tutor_service import (
    backfill_content_source_origin,
    get_db_health_snapshot,
    get_learner_profile_snapshot,
    handle_recommend_request,
    handle_tutor_request,
    handle_tutor_request_stream,
    ingest_source_items,
    list_ingestion_history_snapshot,
    list_content_items_snapshot,
    reset_learner_state,
)
from fastapi_app.schemas.learner import (
    BackfillSourceOriginResponse,
    ContentItemsResponse,
    CurriculumResponse,
    CurriculumUpdateRequest,
    IngestSourcesRequest,
    IngestSourcesResponse,
    IngestionHistoryResponse,
    LearnerProfileResponse,
    ModuleProgressUpdate,
    TutorChatRequest,
    TutorChatResponse,
    TutorRecommendRequest,
    TutorRecommendResponse,
)
from fastapi_app.schemas.platform import KnowledgePatchRequest, KnowledgeSeedRequest
from fastapi_app.security import (
    AuthContext,
    assert_profile_access,
    get_auth_context,
    require_api_key,
    require_dev_token,
    resolve_learner_id,
)
from fastapi_app.database import get_db
from fastapi_app.services import knowledge_service, onboarding_service, sessions_service
from fastapi_app.services.content_ingestion_service import run_ingestion_for_topics
from fastapi_app.services.curriculum_service import get_curriculum_for_course
from fastapi_app.services.course_service import get_learner_enrolled_courses
from fastapi_app.services.engagement_service import record_engagement
from fastapi_app.services.module_progress_service import upsert_module_progress

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tutor", tags=["AI Tutor"])


@router.post("/chat")
async def tutor_chat(
    payload: TutorChatRequest,
    auth: AuthContext = Depends(get_auth_context),
    stream: bool = Query(default=False),
):
    """Full multi-agent tutoring chat via CoordinatorAgent. Supports JWT or API key."""
    learner_id = resolve_learner_id(auth, payload.learner_id)
    if stream:
        return await _tutor_chat_stream_response(
            TutorChatRequest(**{**payload.model_dump(), "learner_id": learner_id}),
            auth,
        )
    try:
        events = [e.model_dump() for e in payload.events] if payload.events else None
        session_id = payload.session_id
        subject = (payload.course_context or {}).get("subject", "General")
        session = sessions_service.get_or_create_session(
            learner_id, session_id=session_id, subject=str(subject)
        )
        result = handle_tutor_request(
            learner_id=learner_id,
            message=payload.message,
            course_context=payload.course_context,
            events=events,
            time_budget_minutes=payload.time_budget_minutes,
        )
        topic = str(subject) if subject != "General" else None
        sessions_service.touch_session(
            learner_id,
            session["session_id"],
            user_message=payload.message,
            assistant_message=result["assistant_message"],
            topic=topic,
        )
        record_engagement(learner_id, "chat_message", {"session_id": session["session_id"]})
        result["session_id"] = session["session_id"]
        return TutorChatResponse(**result)
    except Exception as exc:
        logger.exception("tutor_chat_failed", extra={"learner_id": learner_id})
        raise HTTPException(status_code=500, detail={"detail": str(exc), "code": "chat_error"}) from exc


@router.post("/chat/stream")
async def tutor_chat_stream_route(
    payload: TutorChatRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    return await _tutor_chat_stream_response(payload, auth)


async def _tutor_chat_stream_response(payload: TutorChatRequest, auth: AuthContext):
    """Stream tutoring chat tokens via Server-Sent Events."""

    learner_id = resolve_learner_id(auth, payload.learner_id)

    async def event_generator():
        events = [e.model_dump() for e in payload.events] if payload.events else None
        subject = (payload.course_context or {}).get("subject", "General")
        session = sessions_service.get_or_create_session(
            learner_id, session_id=payload.session_id, subject=str(subject)
        )
        session_id = session["session_id"]
        topic = str(subject) if subject != "General" else None
        final_message = ""

        try:
            async for chunk in handle_tutor_request_stream(
                learner_id=learner_id,
                message=payload.message,
                course_context=payload.course_context,
                events=events,
                time_budget_minutes=payload.time_budget_minutes,
            ):
                if chunk.get("type") == "delta":
                    yield f"data: {json.dumps({'delta': chunk.get('content', ''), 'done': False}, default=str)}\n\n"
                elif chunk.get("type") == "done":
                    final_message = chunk.get("assistant_message", "")
                    yield f"data: {json.dumps({'delta': '', 'done': True, 'full_response': final_message, 'session_id': session_id}, default=str)}\n\n"
                else:
                    yield f"data: {json.dumps(chunk, default=str)}\n\n"
        except Exception as exc:
            logger.exception("tutor_chat_stream_failed", extra={"learner_id": learner_id})
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"
            return

        if final_message:
            sessions_service.touch_session(
                learner_id,
                session_id,
                user_message=payload.message,
                assistant_message=final_message,
                topic=topic,
            )
            record_engagement(learner_id, "chat_message", {"session_id": session_id})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/recommend", response_model=TutorRecommendResponse)
def tutor_recommend(
    payload: TutorRecommendRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> TutorRecommendResponse:
    """
    Direct recommendations without full Coordinator orchestration.

    Uses deterministic hybrid ranking by default (no OpenAI required).
    """
    try:
        events = [e.model_dump() for e in payload.events] if payload.events else None
        learner_id = resolve_learner_id(auth, payload.learner_id)
        enrolled = get_learner_enrolled_courses(learner_id, db)

        message = payload.message or "what should I study next"
        course_context = dict(payload.course_context or {})
        if enrolled:
            course_context["enrolled_courses"] = enrolled
            course_titles = ", ".join(f"{c['code']} {c['title']}" for c in enrolled)
            message = (
                f"{message}\n\n"
                f"[CONTEXT: Student is enrolled in: {course_titles}. "
                f"Prioritize resources relevant to these specific courses.]"
            )

        result = handle_recommend_request(
            learner_id=learner_id,
            message=message,
            course_context=course_context,
            events=events,
            limit=payload.limit,
            use_agent=payload.use_agent,
            enrolled_courses=enrolled,
        )
        return TutorRecommendResponse(
            request_id=result["request_id"],
            learner_id=result["learner_id"],
            source=result["source"],
            recommendations=result.get("recommendations", []),
            adaptive_path=result.get("adaptive_path", []),
            memory_used=result.get("memory_used"),
            timestamp=result["timestamp"],
            status=result.get("status"),
            message=result.get("message"),
        )
    except Exception as exc:
        logger.exception("tutor_recommend_failed", extra={"learner_id": payload.learner_id})
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/curriculum/{learner_id}", response_model=CurriculumResponse)
def get_curriculum(
    learner_id: str,
    course_id: str = Query(..., description="Enrolled course UUID"),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> CurriculumResponse:
    """Per-course curriculum built from content matching that course's title only."""
    resolved_id = resolve_learner_id(auth, learner_id)
    try:
        result = get_curriculum_for_course(resolved_id, course_id, db)
        if result.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Course not found")
        if result.get("status") == "not_enrolled":
            raise HTTPException(status_code=403, detail=result.get("message", "Not enrolled"))
        return CurriculumResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_curriculum_failed", extra={"learner_id": resolved_id, "course_id": course_id})
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/curriculum/request-update")
def request_curriculum_update(
    payload: CurriculumUpdateRequest,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    """Trigger ingestion for a single course's topic, then refetch curriculum."""
    from fastapi_app.admin.models import Course
    from fastapi_app.services.course_service import get_course_ids_for_learner

    learner_id = resolve_learner_id(auth, payload.learner_id)
    enrolled_ids = get_course_ids_for_learner(learner_id)
    if payload.course_id not in enrolled_ids:
        raise HTTPException(status_code=403, detail="You are not enrolled in this course")

    course = db.get(Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    background_tasks.add_task(
        run_ingestion_for_topics,
        [course.course_title],
        3,
    )
    return {
        "message": f"Update requested for {course.course_code}",
        "status": "processing",
        "course_id": course.id,
        "course_code": course.course_code,
    }


@router.post("/module-progress")
def update_module_progress(
    payload: ModuleProgressUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    """Update per-module progress for a learner."""
    from agency.core.tools.models import ContentItem

    learner_id = resolve_learner_id(auth, payload.learner_id or "")
    if not learner_id:
        raise HTTPException(status_code=400, detail="learner_id is required")

    item = db.get(ContentItem, payload.content_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content item not found")

    if payload.status not in {"not_started", "in_progress", "completed"}:
        raise HTTPException(status_code=400, detail="Invalid status")

    upsert_module_progress(
        db,
        learner_id=learner_id,
        content_item_id=payload.content_item_id,
        percent_complete=payload.percent_complete,
        status=payload.status,
    )
    return {"message": "Progress updated", "content_item_id": payload.content_item_id}


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ai-tutor-backend"}


@router.get("/profile/{learner_id}", response_model=LearnerProfileResponse)
def learner_profile(
    learner_id: str,
    auth: AuthContext = Depends(get_auth_context),
) -> LearnerProfileResponse:
    """Debug endpoint to inspect per-learner personalization state."""
    try:
        assert_profile_access(auth, learner_id)
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
