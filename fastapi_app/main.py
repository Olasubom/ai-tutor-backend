"""
FastAPI entrypoint for the AI Tutor backend.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure project root is on PYTHONPATH when running via uvicorn
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / "agency" / ".env", override=True)

from fastapi_app.routers.tutor_router import router as tutor_router  # noqa: E402
from fastapi_app.routers.quiz import router as quiz_router  # noqa: E402
from fastapi_app.routers.notifications import router as notifications_router  # noqa: E402
from fastapi_app.routers.sessions import router as sessions_router  # noqa: E402
from fastapi_app.routers.goals import router as goals_router  # noqa: E402
from fastapi_app.routers.memory_profile import router as memory_profile_router  # noqa: E402
from fastapi_app.routers.at_risk import router as at_risk_router  # noqa: E402
from fastapi_app.routers.engagement import router as engagement_router  # noqa: E402
from fastapi_app.routers.platform_tasks import router as platform_tasks_router  # noqa: E402
from fastapi_app.routers.onboarding import router as onboarding_router  # noqa: E402
from fastapi_app.routers.lecturer import router as lecturer_router  # noqa: E402
from fastapi_app.routers.admin_catalog import router as admin_catalog_router  # noqa: E402
from fastapi_app.routers.auth_profile import router as auth_profile_router  # noqa: E402
from fastapi_app.services.memory_files import ensure_memory_dirs  # noqa: E402
from agency.core.context import get_runtime  # noqa: E402
from agency.core.tools.database import Database  # noqa: E402
from agency.core.utils import configure_logging  # noqa: E402

configure_logging()

app = FastAPI(
    title="AI Tutor Backend",
    description="Adaptive learning tutor powered by Agency Swarm + OpenAI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tutor_router)
app.include_router(quiz_router)
app.include_router(notifications_router)
app.include_router(sessions_router)
app.include_router(goals_router)
app.include_router(memory_profile_router)
app.include_router(at_risk_router)
app.include_router(engagement_router)
app.include_router(platform_tasks_router)
app.include_router(onboarding_router)
app.include_router(lecturer_router)
app.include_router(admin_catalog_router)
app.include_router(auth_profile_router)


@app.on_event("startup")
def startup_memory_dirs() -> None:
    ensure_memory_dirs()


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/")
def root() -> dict:
    return {"service": "AI Tutor Backend", "docs": "/docs"}


@app.get("/healthz")
def healthz() -> dict:
    """Basic liveness endpoint for containers and load balancers."""
    return {"status": "ok", "service": "AI Tutor Backend"}


@app.get("/readyz")
def readyz() -> JSONResponse:
    """
    Readiness endpoint with dependency checks.

    Returns 200 when all critical components are healthy, otherwise 503.
    """
    checks = {
        "database": False,
        "catalog_loaded": False,
        "vector_store": False,
    }
    details = {}

    # Database connectivity
    try:
        db = Database()
        with db.engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        checks["database"] = True
    except Exception as exc:
        details["database_error"] = str(exc)

    # Runtime checks
    try:
        runtime = get_runtime()
        checks["catalog_loaded"] = len(runtime.catalog) > 0
        checks["vector_store"] = runtime.vector_store is not None
    except Exception as exc:
        details["runtime_error"] = str(exc)

    payload = {
        "status": "ready" if all(checks.values()) else "not_ready",
        "checks": checks,
        "openai_key_configured": bool(
            os.getenv("OPENAI_API_KEY")
            and "your_key_here" not in os.getenv("OPENAI_API_KEY", "").lower()
        ),
    }
    if details:
        payload["details"] = details

    return JSONResponse(status_code=200 if payload["status"] == "ready" else 503, content=payload)
