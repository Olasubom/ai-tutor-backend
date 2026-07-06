from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PerformanceEvent(BaseModel):
    topic: str
    correct: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TutorChatRequest(BaseModel):
    learner_id: str = Field(..., description="Stable learner identifier")
    message: str = Field(..., description="Learner's latest message")
    session_id: Optional[str] = Field(default=None, description="Active chat session id")
    course_context: Optional[Dict[str, Any]] = Field(
        default=None, description="Subject, level, goals, curriculum"
    )
    events: Optional[List[PerformanceEvent]] = Field(
        default=None, description="Recent quiz/performance events"
    )
    time_budget_minutes: Optional[int] = Field(
        default=None, description="Available study time for planning"
    )


class TutorChatResponse(BaseModel):
    request_id: str
    learner_id: str
    assistant_message: str
    session_id: Optional[str] = None
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class TutorRecommendRequest(BaseModel):
    learner_id: str = Field(..., description="Stable learner identifier")
    message: str = Field(
        default="what should I study next",
        description="Query used for memory retrieval and ranking context",
    )
    course_context: Optional[Dict[str, Any]] = None
    events: Optional[List[PerformanceEvent]] = None
    limit: int = Field(default=6, ge=1, le=12)
    use_agent: bool = Field(
        default=False,
        description="If true and OPENAI_API_KEY is set, call RecommendationAgent via Agency Swarm",
    )


class TutorRecommendResponse(BaseModel):
    request_id: str
    learner_id: str
    source: str
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    adaptive_path: List[Dict[str, Any]] = Field(default_factory=list)
    memory_used: Optional[Dict[str, Any]] = None
    timestamp: str
    status: Optional[str] = None
    message: Optional[str] = None


class LearnerProfileResponse(BaseModel):
    learner_id: str
    profile: Dict[str, Any] = Field(default_factory=dict)
    memory: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class IngestSourcesRequest(BaseModel):
    source: str = Field(
        default="all",
        description="Source to ingest from: youtube, ebooks, or all",
    )
    topics: Optional[List[str]] = Field(
        default=None,
        description="Optional list of topics; falls back to catalog topics if omitted",
    )
    max_per_topic: int = Field(default=5, ge=1, le=20)


class IngestSourcesResponse(BaseModel):
    source: str
    topics: List[str] = Field(default_factory=list)
    fetched: int
    deduped: int
    written: int
    catalog_size: int
    timestamp: str


class ContentItemsResponse(BaseModel):
    filters: Dict[str, Any] = Field(default_factory=dict)
    count: int
    items: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: str


class IngestionHistoryResponse(BaseModel):
    count: int
    runs: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: str


class BackfillSourceOriginResponse(BaseModel):
    counts: Dict[str, int] = Field(default_factory=dict)
    catalog_size: int
    timestamp: str


class CurriculumResponse(BaseModel):
    learner_id: str
    course_id: str
    course_code: str
    course_title: str
    modules: List[Dict[str, Any]] = Field(default_factory=list)
    source: Optional[str] = None
    status: str
    message: Optional[str] = None


class CurriculumUpdateRequest(BaseModel):
    learner_id: str
    course_id: str


class ModuleProgressUpdate(BaseModel):
    learner_id: Optional[str] = None
    content_item_id: str
    percent_complete: int = Field(ge=0, le=100)
    status: str


class StartModuleSessionRequest(BaseModel):
    content_item_id: str


class ContinueModuleSessionRequest(BaseModel):
    session_id: str
    message: Optional[str] = None
    selected_option_id: Optional[str] = None


class CompleteModuleSessionRequest(BaseModel):
    session_id: str
