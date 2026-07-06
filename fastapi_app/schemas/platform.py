from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QuizGenerateRequest(BaseModel):
    learner_id: str
    topic: str
    num_questions: int = 5


class QuizResponseItem(BaseModel):
    question_id: str
    selected_option: int
    time_taken_seconds: int = 0


class QuizSubmitRequest(BaseModel):
    learner_id: str
    quiz_id: str
    responses: List[QuizResponseItem]
    content_item_id: Optional[str] = None


class GradeShortAnswerRequest(BaseModel):
    question: str
    model_answer: str
    key_points: List[str] = Field(default_factory=list)
    student_answer: str
    content_item_id: str


class EngagementRequest(BaseModel):
    event_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GoalCreateRequest(BaseModel):
    topic: str
    target_mastery: float = Field(ge=0.0, le=1.0)
    target_date: str


class TaskCreateRequest(BaseModel):
    text: str
    due_date: str
    priority: str = "medium"
    course: str = "General"


class KnowledgePatchRequest(BaseModel):
    proficiency: str


class OnboardingStep1(BaseModel):
    learner_id: str
    full_name: str
    field_of_study: str
    institution: str
    proficiency_level: str


class OnboardingStep2(BaseModel):
    learner_id: str
    department_id: str
    level: str
    selected_course_ids: List[str] = Field(default_factory=list)
    additional_subjects: List[str] = Field(default_factory=list)


class OnboardingStep4(BaseModel):
    learner_id: str
    weekly_hours: int
    content_formats: List[str] = Field(default_factory=list)
    primary_objective: str


class KnowledgeSeedRequest(BaseModel):
    learner_id: str
    assessments: List[Dict[str, str]]


class SendResourceRequest(BaseModel):
    lecturer_id: str
    learner_id: str
    resource_url: str
    note: Optional[str] = None


class LecturerEnsureRequest(BaseModel):
    name: str
    department_id: str
    faculty_id: Optional[str] = None


class TutorChatRequestExtended(BaseModel):
    learner_id: str
    message: str
    session_id: Optional[str] = None
    course_context: Optional[Dict[str, Any]] = None
    events: Optional[List[Dict[str, Any]]] = None
    time_budget_minutes: Optional[int] = None
