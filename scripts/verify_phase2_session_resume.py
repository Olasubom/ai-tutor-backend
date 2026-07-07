#!/usr/bin/env python3
"""Verify Phase 2: session resume preserves quiz/completed state."""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / "agency" / ".env", override=False)

from sqlalchemy import select

from agency.core.tools.database import Database
from agency.core.tools.models import ContentItem, ModuleSession
from fastapi_app.bootstrap import init_database
from fastapi_app.services import module_session_service as mss


def _upsert_session(
    session,
    *,
    learner_id: str,
    item: ContentItem,
    stage: str,
    session_data: dict,
    explanation_progress: int = 0,
) -> ModuleSession:
    mod = session.scalar(
        select(ModuleSession).where(
            ModuleSession.learner_id == learner_id,
            ModuleSession.content_item_id == item.item_id,
        )
    )
    if mod:
        session.delete(mod)
        session.commit()
    mod = ModuleSession(
        learner_id=learner_id,
        content_item_id=item.item_id,
        course_id=item.course_id,
        stage=stage,
        explanation_progress=explanation_progress,
        session_data=json.dumps(session_data),
    )
    session.add(mod)
    session.commit()
    session.refresh(mod)
    return mod


def main() -> None:
    init_database()
    db = Database()

    with db._SessionLocal() as session:  # noqa: SLF001
        item = session.scalar(select(ContentItem).where(ContentItem.title.ilike("%Module2%")))
        if not item:
            raise SystemExit("Module2 not found")

        quiz_id = "abc12345"
        quiz_data = {"mcq": [{"id": "q1"}], "short_answer": []}

        # Quiz stage resume preserves quiz_id/quiz_data
        learner_quiz = "phase2-verify-quiz"
        _upsert_session(
            session,
            learner_id=learner_quiz,
            item=item,
            stage="quiz",
            explanation_progress=7,
            session_data={
                "chunks_delivered_count": 7,
                "topic_index": 7,
                "quiz_id": quiz_id,
                "quiz_data": quiz_data,
                "topics_covered": ["Topic A"],
            },
        )
        resume_quiz = mss.start_or_resume_session(
            learner_id=learner_quiz, content_item_id=item.item_id, db=session
        )
        assert resume_quiz["stage"] == "quiz", resume_quiz
        assert resume_quiz.get("quiz_id") == quiz_id, resume_quiz
        assert resume_quiz.get("quiz_data") == quiz_data, resume_quiz
        print("Quiz revisit: preserved quiz_id and quiz_data")

        # Completed stage resume
        learner_done = "phase2-verify-done"
        _upsert_session(
            session,
            learner_id=learner_done,
            item=item,
            stage="completed",
            explanation_progress=7,
            session_data={
                "chunks_delivered_count": 7,
                "topic_index": 7,
                "quiz_id": quiz_id,
                "quiz_data": quiz_data,
            },
        )
        resume_done = mss.start_or_resume_session(
            learner_id=learner_done, content_item_id=item.item_id, db=session
        )
        assert resume_done["stage"] == "completed", resume_done
        print("Completed revisit: shows completed state")

        # Abandoned onboarding still restarts
        learner_onb = "phase2-verify-onb"
        _upsert_session(
            session,
            learner_id=learner_onb,
            item=item,
            stage="onboarding",
            session_data={
                "chunks_delivered_count": 0,
                "topic_index": 0,
                "onboarding_step": "style",
            },
        )
        resume_onb = mss.start_or_resume_session(
            learner_id=learner_onb, content_item_id=item.item_id, db=session
        )
        assert resume_onb["stage"] == "onboarding", resume_onb
        assert resume_onb.get("onboarding_step") == "style", resume_onb
        print("Abandoned onboarding: restarts onboarding flow")

        # Single-topic module at quiz with chunks_delivered=1 must NOT reset
        learner_single = "phase2-verify-single-chunk"
        _upsert_session(
            session,
            learner_id=learner_single,
            item=item,
            stage="quiz",
            explanation_progress=1,
            session_data={
                "chunks_delivered_count": 1,
                "topic_index": 1,
                "quiz_id": quiz_id,
                "quiz_data": quiz_data,
            },
        )
        resume_single = mss.start_or_resume_session(
            learner_id=learner_single, content_item_id=item.item_id, db=session
        )
        assert resume_single["stage"] == "quiz", resume_single
        assert resume_single.get("quiz_id") == quiz_id, resume_single
        print("Quiz with chunks_delivered=1: no erroneous reset")

        for lid in [learner_quiz, learner_done, learner_onb, learner_single]:
            row = session.scalar(select(ModuleSession).where(ModuleSession.learner_id == lid))
            if row:
                session.delete(row)
        session.commit()

    print("PHASE 2 VERIFY: PASS")


if __name__ == "__main__":
    main()
