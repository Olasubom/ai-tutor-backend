from __future__ import annotations

import random
import string
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi_app.services.memory_files import append_jsonl, read_json, read_jsonl, write_json


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_session_id(learner_id: str) -> str:
    prefix = learner_id.replace("learner_", "")[:4].upper()
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"SESS-{prefix}-{suffix}"


def list_sessions(learner_id: str) -> List[dict]:
    return read_json(f"sessions/{learner_id}.json", [])


def get_or_create_session(learner_id: str, session_id: Optional[str] = None, subject: str = "General") -> dict:
    sessions = list_sessions(learner_id)
    today = datetime.now(timezone.utc).date().isoformat()

    if session_id:
        for s in sessions:
            if s.get("session_id") == session_id:
                return s

    for s in sessions:
        started = str(s.get("started_at", ""))[:10]
        if started == today and not session_id:
            return s

    session = {
        "session_id": session_id or _new_session_id(learner_id),
        "subject": subject,
        "started_at": _now(),
        "ended_at": _now(),
        "message_count": 0,
        "topics_covered": [],
        "summary": "",
    }
    sessions.append(session)
    write_json(f"sessions/{learner_id}.json", sessions)
    return session


def touch_session(
    learner_id: str,
    session_id: str,
    *,
    user_message: str,
    assistant_message: str,
    topic: Optional[str] = None,
) -> dict:
    sessions = list_sessions(learner_id)
    session = None
    for s in sessions:
        if s.get("session_id") == session_id:
            session = s
            break
    if not session:
        session = get_or_create_session(learner_id, session_id=session_id)
        sessions = list_sessions(learner_id)

    session["message_count"] = int(session.get("message_count", 0)) + 2
    session["ended_at"] = _now()
    if topic and topic not in session.get("topics_covered", []):
        session.setdefault("topics_covered", []).append(topic)
    if assistant_message and not session.get("summary"):
        session["summary"] = assistant_message[:120]

    for i, s in enumerate(sessions):
        if s.get("session_id") == session_id:
            sessions[i] = session
            break
    else:
        sessions.append(session)

    write_json(f"sessions/{learner_id}.json", sessions)

    append_jsonl(
        f"chat/{learner_id}/{session_id}.jsonl",
        {"role": "user", "content": user_message, "timestamp": _now()},
    )
    append_jsonl(
        f"chat/{learner_id}/{session_id}.jsonl",
        {"role": "assistant", "content": assistant_message, "timestamp": _now()},
    )
    return session


def get_session_messages(learner_id: str, session_id: str) -> List[dict]:
    return read_jsonl(f"chat/{learner_id}/{session_id}.jsonl")
