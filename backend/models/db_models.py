import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String, nullable=False)          # google | github | facebook
    provider_user_id: Mapped[str] = mapped_column(String, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, nullable=False, default="student")  # admin | student
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deactivated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    enrollments: Mapped[list["UserEnrollment"]] = relationship("UserEnrollment", foreign_keys="UserEnrollment.user_id", back_populates="user")
    progress: Mapped[list["UserProgress"]] = relationship("UserProgress", back_populates="user")
    view_logs: Mapped[list["CourseViewLog"]] = relationship("CourseViewLog", back_populates="user")


# ---------------------------------------------------------------------------
# User Enrollments (admin-managed course access)
# ---------------------------------------------------------------------------
class UserEnrollment(Base):
    __tablename__ = "user_enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    enrolled_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    removed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="enrollments")
    course: Mapped["Course"] = relationship("Course", back_populates="enrollments")


# ---------------------------------------------------------------------------
# Knowledge Assets & Chunks
# ---------------------------------------------------------------------------
class KnowledgeAsset(Base):
    __tablename__ = "knowledge_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)   # pdf | url | wiki | image
    source_uri: Mapped[str | None] = mapped_column(String)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chunks: Mapped[list["DocumentChunk"]] = relationship("DocumentChunk", back_populates="asset", cascade="all, delete")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_assets.id", ondelete="CASCADE"), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int | None] = mapped_column(Integer)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    asset: Mapped["KnowledgeAsset"] = relationship("KnowledgeAsset", back_populates="chunks")


# ---------------------------------------------------------------------------
# Learning Paths & Courses
# ---------------------------------------------------------------------------
class LearningPath(Base):
    __tablename__ = "learning_paths"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    courses: Mapped[list["Course"]] = relationship("Course", back_populates="path", cascade="all, delete")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("learning_paths.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(String)
    sequence_order: Mapped[int | None] = mapped_column(Integer)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    path: Mapped["LearningPath"] = relationship("LearningPath", back_populates="courses")
    videos: Mapped[list["CourseVideo"]] = relationship("CourseVideo", back_populates="course", cascade="all, delete")
    enrollments: Mapped[list["UserEnrollment"]] = relationship("UserEnrollment", back_populates="course")
    progress: Mapped[list["UserProgress"]] = relationship("UserProgress", back_populates="course")
    assessments: Mapped[list["Assessment"]] = relationship("Assessment", back_populates="course")


# ---------------------------------------------------------------------------
# Course Videos
# ---------------------------------------------------------------------------
class CourseVideo(Base):
    __tablename__ = "course_videos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str] = mapped_column(String, nullable=False)
    duration_secs: Mapped[int | None] = mapped_column(Integer)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    course: Mapped["Course"] = relationship("Course", back_populates="videos")
    progress_records: Mapped[list["VideoProgress"]] = relationship("VideoProgress", back_populates="video", cascade="all, delete")
    view_logs: Mapped[list["CourseViewLog"]] = relationship("CourseViewLog", back_populates="video")


# ---------------------------------------------------------------------------
# Video Progress (resume from last position)
# ---------------------------------------------------------------------------
class VideoProgress(Base):
    __tablename__ = "video_progress"
    __table_args__ = (UniqueConstraint("user_id", "video_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("course_videos.id", ondelete="CASCADE"), nullable=False)
    last_position_secs: Mapped[int] = mapped_column(Integer, default=0)
    watch_percent: Mapped[float] = mapped_column(Float, default=0.0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    last_watched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    video: Mapped["CourseVideo"] = relationship("CourseVideo", back_populates="progress_records")


# ---------------------------------------------------------------------------
# Course View Audit Log
# ---------------------------------------------------------------------------
class CourseViewLog(Base):
    __tablename__ = "course_view_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    course_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"))
    video_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("course_videos.id"))
    session_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    session_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_secs: Mapped[int | None] = mapped_column(Integer)
    device_info: Mapped[str | None] = mapped_column(String)
    ip_address: Mapped[str | None] = mapped_column(String)

    user: Mapped["User"] = relationship("User", back_populates="view_logs")
    course: Mapped["Course"] = relationship("Course")
    video: Mapped["CourseVideo"] = relationship("CourseVideo", back_populates="view_logs")


# ---------------------------------------------------------------------------
# User Progress (course-level rollup)
# ---------------------------------------------------------------------------
class UserProgress(Base):
    __tablename__ = "user_progress"
    __table_args__ = (UniqueConstraint("user_id", "course_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default="not_started")  # not_started | in_progress | completed
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship("User", back_populates="progress")
    course: Mapped["Course"] = relationship("Course", back_populates="progress")


# ---------------------------------------------------------------------------
# Assessments & Questions
# ---------------------------------------------------------------------------
class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)           # mcq | free_form | mixed

    course: Mapped["Course"] = relationship("Course", back_populates="assessments")
    questions: Mapped[list["Question"]] = relationship("Question", back_populates="assessment", cascade="all, delete")
    attempts: Mapped[list["AssessmentAttempt"]] = relationship("AssessmentAttempt", back_populates="assessment")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String, nullable=False)  # mcq | free_form
    options: Mapped[dict | None] = mapped_column(JSONB)                 # [{label, text, is_correct}]
    rubric: Mapped[str | None] = mapped_column(Text)
    correct_answer: Mapped[str | None] = mapped_column(Text)
    max_score: Mapped[int] = mapped_column(Integer, default=10)

    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="questions")


# ---------------------------------------------------------------------------
# Assessment Attempts & Answers
# ---------------------------------------------------------------------------
class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assessment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_score: Mapped[int | None] = mapped_column(Integer)
    passed: Mapped[bool | None] = mapped_column(Boolean)

    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="attempts")
    answers: Mapped[list["AnswerRecord"]] = relationship("AnswerRecord", back_populates="attempt", cascade="all, delete")


class AnswerRecord(Base):
    __tablename__ = "answer_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("questions.id"), nullable=False)
    student_answer: Mapped[str | None] = mapped_column(Text)
    score: Mapped[int | None] = mapped_column(Integer)
    ai_reasoning: Mapped[str | None] = mapped_column(Text)
    pass_1_concepts: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    attempt: Mapped["AssessmentAttempt"] = relationship("AssessmentAttempt", back_populates="answers")


# ---------------------------------------------------------------------------
# Chat History (LangChain-compatible)
# ---------------------------------------------------------------------------
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String, nullable=False)           # human | ai
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
