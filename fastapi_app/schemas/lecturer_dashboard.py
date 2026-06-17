"""Pydantic schemas for lecturer dashboard APIs."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    code: str
    title: str
    description: Optional[str] = None
    level: str = "100"
    college: Optional[str] = None
    department: Optional[str] = None


class CourseUpdate(BaseModel):
    code: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    level: Optional[str] = None


class ModuleCreate(BaseModel):
    title: str
    description: Optional[str] = None
    order: int = 1
    bloom_level: Optional[str] = None


class ModuleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    bloom_level: Optional[str] = None


class ModuleReorderRequest(BaseModel):
    order: int


class QuizCreate(BaseModel):
    title: str
    description: Optional[str] = None
    bloom_level: Optional[str] = None
    time_limit_minutes: Optional[int] = None
    max_attempts: int = 3


class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    bloom_level: Optional[str] = None
    time_limit_minutes: Optional[int] = None
    max_attempts: Optional[int] = None


class QuestionOptionCreate(BaseModel):
    text: str
    is_correct: bool = False


class QuestionCreate(BaseModel):
    text: str
    question_type: str = "mcq"
    order: Optional[int] = None
    difficulty: str = "medium"
    explanation: Optional[str] = None
    options: List[QuestionOptionCreate] = Field(default_factory=list)


class QuestionUpdate(BaseModel):
    text: Optional[str] = None
    difficulty: Optional[str] = None
    explanation: Optional[str] = None
    options: Optional[List[QuestionOptionCreate]] = None


class GenerateQuestionsRequest(BaseModel):
    topic: Optional[str] = None
    count: int = Field(default=5, ge=1, le=20)
    difficulty: str = "medium"
    bloom_level: str = "understand"


class QuizSubmitAnswersRequest(BaseModel):
    answers: Dict[str, str]


class GradeCreate(BaseModel):
    student_id: str
    ca_score: Optional[float] = None
    exam_score: Optional[float] = None
    comment: Optional[str] = None


class GradeUpdate(BaseModel):
    ca_score: Optional[float] = None
    exam_score: Optional[float] = None
    comment: Optional[str] = None


class AnnouncementCreate(BaseModel):
    title: str
    body: str
    is_pinned: bool = False


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    is_pinned: Optional[bool] = None
