from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_request_id() -> str:
    return str(uuid.uuid4())


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for k, v in record.__dict__.items():
            if k.startswith("_"):
                continue
            if k in {"msg", "args", "levelname", "levelno", "name", "pathname", "filename", "module", "exc_info",
                     "exc_text", "stack_info", "lineno", "funcName", "created", "msecs", "relativeCreated",
                     "thread", "threadName", "processName", "process"}:
                continue
            if k not in payload:
                try:
                    json.dumps(v)
                    payload[k] = v
                except TypeError:
                    payload[k] = str(v)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: Optional[str] = None) -> None:
    log_level = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    root = logging.getLogger()
    root.setLevel(log_level)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.handlers.clear()
    root.addHandler(handler)

