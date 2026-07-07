#!/usr/bin/env python3
"""Verify Phase 1: all topics delivered before tasks stage."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

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


def main() -> None:
    init_database()
    db = Database()
    learner_id = "phase1-verify-learner"

    with db._SessionLocal() as session:  # noqa: SLF001
        item = session.scalar(select(ContentItem).where(ContentItem.title.ilike("%Module2%")))
        if not item:
            raise SystemExit("Module2 not found")

        topics = mss._get_topics_for_module(item, session)
        total = len(topics)
        print(f"Module: {item.title} | topics={total}")

        existing = session.scalar(
            select(ModuleSession).where(
                ModuleSession.learner_id == learner_id,
                ModuleSession.content_item_id == item.item_id,
            )
        )
        if existing:
            session.delete(existing)
            session.commit()

        def fake_deliver(**kwargs):
            idx = kwargs["topic_index"]
            return f"Topic {idx + 1} of {total} delivered"

        with patch.object(mss, "_deliver_topic", side_effect=fake_deliver):
            with patch.object(mss, "_append_to_chat_session"):
                start = mss.start_or_resume_session(
                    learner_id=learner_id, content_item_id=item.item_id, db=session
                )
                assert start["stage"] == "onboarding", start

                mod = session.scalar(
                    select(ModuleSession).where(
                        ModuleSession.learner_id == learner_id,
                        ModuleSession.content_item_id == item.item_id,
                    )
                )
                mss.handle_onboarding_selection(mod, item, "step_by_step", session)
                session.refresh(mod)
                result = mss.handle_onboarding_selection(mod, item, "beginner", session)
                session.refresh(mod)
                assert result["stage"] == "explanation", result
                print(f"After onboarding: progress {result.get('explanation_progress')} of {total}")

                for i in range(total - 1):
                    session.refresh(mod)
                    data = json.loads(mod.session_data)
                    r = mss.handle_explanation_stage(mod, item, "next", session)
                    session.refresh(mod)
                    assert r["stage"] == "explanation", (i, r)
                    print(
                        f"  next #{i + 1}: stage={r['stage']} "
                        f"progress={r.get('explanation_progress')} "
                        f"(topic_index was {data['topic_index']})"
                    )

                session.refresh(mod)
                data = json.loads(mod.session_data)
                assert data["topic_index"] == total, data
                r = mss.handle_explanation_stage(mod, item, "next", session)
                assert r["stage"] != "explanation", r
                print(f"  final next: stage={r['stage']} after all {total} topics delivered")

                session.delete(mod)
                session.commit()

        mod = ModuleSession(
            learner_id=learner_id + "-q",
            content_item_id=item.item_id,
            course_id=item.course_id,
            stage="explanation",
            explanation_progress=2,
            session_data=json.dumps(
                {
                    "chunks_delivered_count": 2,
                    "topic_index": 2,
                    "onboarding_style": "step_by_step",
                    "onboarding_level": "beginner",
                    "topics_covered": [t["title"] for t in topics[:2]],
                }
            ),
        )
        session.add(mod)
        session.commit()
        session.refresh(mod)
        q = "Why does acceptance need to mirror the offer terms exactly?"
        with patch.object(mss, "_deliver_topic", return_value="Addressed question then continued"):
            with patch.object(mss, "_append_to_chat_session"):
                rq = mss.handle_explanation_stage(mod, item, q, session)
        assert rq["stage"] == "explanation", rq
        print("Off-topic question: stayed in explanation")

        for lid in [learner_id, learner_id + "-q"]:
            row = session.scalar(select(ModuleSession).where(ModuleSession.learner_id == lid))
            if row:
                session.delete(row)
        session.commit()

    print("PHASE 1 VERIFY: PASS")


if __name__ == "__main__":
    main()
