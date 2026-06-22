import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------
class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    avatar_url: str | None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------------------
# Enrollments
# ---------------------------------------------------------------------------
class EnrollmentIn(BaseModel):
    course_id: uuid.UUID


class EnrollmentOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    course_id: uuid.UUID
    enrolled_at: datetime
    enrolled_by: uuid.UUID | None
    removed_at: datetime | None
    removed_by: uuid.UUID | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Learning Paths
# ---------------------------------------------------------------------------
class LearningPathIn(BaseModel):
    title: str
    description: str | None = None


class LearningPathOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------
class CourseIn(BaseModel):
    path_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    thumbnail_url: str | None = None
    sequence_order: int | None = None


class CourseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    thumbnail_url: str | None = None
    sequence_order: int | None = None


class CourseOut(BaseModel):
    id: uuid.UUID
    path_id: uuid.UUID | None
    title: str
    description: str | None
    thumbnail_url: str | None
    sequence_order: int | None
    is_published: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Course Videos
# ---------------------------------------------------------------------------
class VideoIn(BaseModel):
    title: str
    description: str | None = None
    video_url: str
    duration_secs: int | None = None
    sequence_order: int


class VideoUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    video_url: str | None = None
    duration_secs: int | None = None
    sequence_order: int | None = None


class VideoOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    description: str | None
    video_url: str
    duration_secs: int | None
    sequence_order: int
    is_published: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Video Progress
# ---------------------------------------------------------------------------
class VideoProgressIn(BaseModel):
    position_secs: int
    watch_percent: float
    completed: bool = False


class VideoProgressOut(BaseModel):
    last_position_secs: int
    watch_percent: float
    completed: bool
    last_watched_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# View Session
# ---------------------------------------------------------------------------
class SessionStartOut(BaseModel):
    session_id: uuid.UUID


class SessionEndIn(BaseModel):
    session_id: uuid.UUID


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------
class ViewLogOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    course_id: uuid.UUID | None
    video_id: uuid.UUID | None
    session_start: datetime
    session_end: datetime | None
    duration_secs: int | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Assessments
# ---------------------------------------------------------------------------
class AssessmentIn(BaseModel):
    course_id: uuid.UUID | None = None
    title: str
    type: str  # mcq | free_form | mixed


class AssessmentOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID | None
    title: str
    type: str

    model_config = {"from_attributes": True}


class QuestionIn(BaseModel):
    question_text: str
    question_type: str        # mcq | free_form
    options: list | None = None
    rubric: str | None = None
    correct_answer: str | None = None
    max_score: int = 10


class QuestionOut(BaseModel):
    id: uuid.UUID
    question_text: str
    question_type: str
    options: list | None
    max_score: int

    model_config = {"from_attributes": True}


class AnswerIn(BaseModel):
    question_id: uuid.UUID
    answer: str


class AttemptSubmitIn(BaseModel):
    assessment_id: uuid.UUID
    answers: list[AnswerIn]


class AnswerFeedback(BaseModel):
    question_id: uuid.UUID
    score: int
    max_score: int
    ai_reasoning: str | None


class AttemptResultOut(BaseModel):
    attempt_id: uuid.UUID
    total_score: int
    max_total: int
    passed: bool
    feedback: list[AnswerFeedback]


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
class ChatMessageIn(BaseModel):
    session_id: str
    message: str


class ChatMessageOut(BaseModel):
    session_id: str
    response: str


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
class IngestURLIn(BaseModel):
    url: str
    source_type: str = "url"   # url | wiki


class IngestOut(BaseModel):
    asset_id: uuid.UUID
    chunks_stored: int
    message: str


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
class SearchIn(BaseModel):
    query: str
    top_k: int = 5


class SearchResultItem(BaseModel):
    chunk_id: uuid.UUID
    text: str
    score: float
    metadata: dict | None


class SearchOut(BaseModel):
    results: list[SearchResultItem]
