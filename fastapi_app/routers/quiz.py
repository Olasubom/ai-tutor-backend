from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from fastapi_app.schemas.platform import QuizGenerateRequest, QuizSubmitRequest
from fastapi_app.security import require_api_key
from fastapi_app.services import quiz_service
from fastapi_app.services import notifications_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/quiz", tags=["Quiz"])


@router.post("/generate")
def generate_quiz(payload: QuizGenerateRequest, _: None = Depends(require_api_key)):
    try:
        result = quiz_service.generate_quiz(
            payload.learner_id, payload.topic, payload.num_questions
        )
        due = quiz_service.review_due(payload.learner_id)
        for item in due:
            if item["topic"] == payload.topic and item.get("days_overdue", 0) >= 0:
                notifications_service.create_notification(
                    payload.learner_id,
                    type="review_due",
                    title=f"Review due: {payload.topic}",
                    body="Spaced repetition review is recommended.",
                    action_url=f"/student/quiz/{payload.topic}",
                )
                break
        return result
    except Exception as exc:
        logger.exception("quiz_generate_failed")
        raise HTTPException(status_code=500, detail={"detail": str(exc), "code": "quiz_generate_error"}) from exc


@router.post("/submit")
def submit_quiz(payload: QuizSubmitRequest, _: None = Depends(require_api_key)):
    try:
        responses = [r.model_dump() for r in payload.responses]
        return quiz_service.submit_quiz(payload.learner_id, payload.quiz_id, responses)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"detail": str(exc), "code": "quiz_not_found"}) from exc
    except Exception as exc:
        logger.exception("quiz_submit_failed")
        raise HTTPException(status_code=500, detail={"detail": str(exc), "code": "quiz_submit_error"}) from exc


@router.get("/history/{learner_id}")
def quiz_history(learner_id: str, _: None = Depends(require_api_key)):
    return quiz_service.quiz_history(learner_id)


@router.get("/bkt/{learner_id}/{topic}")
def quiz_bkt(learner_id: str, topic: str, _: None = Depends(require_api_key)):
    return quiz_service.get_bkt_state(learner_id, topic)


@router.get("/review-due/{learner_id}")
def review_due(learner_id: str, _: None = Depends(require_api_key)):
    return quiz_service.review_due(learner_id)
