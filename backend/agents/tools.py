"""LangChain Tools for LMS Backend Capabilities."""
import json
import logging
import uuid
from typing import Any

from langchain_core.tools import StructuredTool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import (
    AssessmentAttempt,
    Course,
    CourseDocument,
    CourseVideo,
    LearningPath,
    UserProgress,
    VideoProgress,
)
from services.assessment_service import grade_free_form
from services.search_service import hybrid_search

logger = logging.getLogger(__name__)


def create_lms_tools(db: AsyncSession, current_user_id: str | None = None) -> list[StructuredTool]:
    """Create bound LangChain StructuredTools for the current DB session and user."""

    async def search_knowledge_base(query: str) -> str:
        """Search course documents, PDFs, presentations, and transcripts for relevant information."""
        try:
            results = await hybrid_search(query=query, db=db, top_k=5)
            if not results:
                return "No relevant documents or course chunks found for this query."

            formatted = []
            for i, r in enumerate(results, 1):
                meta = r.get("metadata") or {}
                source_name = meta.get("filename") or meta.get("source") or meta.get("source_url") or "Document"
                page = f" (Page {meta.get('page')})" if meta.get("page") else ""
                slide = f" (Slide {meta.get('slide')})" if meta.get("slide") else ""
                formatted.append(f"[Source {i}: {source_name}{page}{slide}]\n{r['text']}")

            return "\n\n".join(formatted)
        except Exception as e:
            logger.error(f"Error in search_knowledge_base tool: {e}")
            return f"Error executing search: {str(e)}"

    async def evaluate_student_answer(
        student_answer: str,
        rubric: str,
        correct_answer: str,
        max_score: int = 10,
    ) -> str:
        """Evaluate a student's free-form assessment answer against a rubric and correct answer."""
        try:
            result = await grade_free_form(
                student_answer=student_answer,
                rubric=rubric,
                correct_answer=correct_answer,
                max_score=max_score,
            )
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error in evaluate_student_answer tool: {e}")
            return json.dumps({"score": 0, "reasoning": f"Evaluation error: {str(e)}", "concepts": []})

    async def query_course_catalog(search_term: str = "") -> str:
        """Query available courses, learning paths, video lectures, and document assets in the LMS."""
        try:
            stmt = select(Course).where(Course.is_published == True)
            res = await db.execute(stmt)
            courses = res.scalars().all()

            if not courses:
                return "No published courses available."

            summary = []
            for c in courses:
                if search_term and search_term.lower() not in c.title.lower() and search_term.lower() not in (c.description or "").lower():
                    continue

                v_res = await db.execute(select(CourseVideo).where(CourseVideo.course_id == c.id))
                videos = v_res.scalars().all()

                d_res = await db.execute(select(CourseDocument).where(CourseDocument.course_id == c.id))
                docs = d_res.scalars().all()

                summary.append(
                    f"• Course: {c.title}\n"
                    f"  Description: {c.description or 'N/A'}\n"
                    f"  Videos ({len(videos)}): {', '.join(v.title for v in videos[:5])}\n"
                    f"  Documents ({len(docs)}): {', '.join(d.filename for d in docs[:5])}"
                )

            return "\n\n".join(summary) if summary else f"No courses matched '{search_term}'."
        except Exception as e:
            logger.error(f"Error in query_course_catalog tool: {e}")
            return f"Error querying course catalog: {str(e)}"

    async def get_user_learning_progress(user_id: str = "") -> str:
        """Fetch course completion status, video watch percentages, and quiz scores for a student."""
        uid_str = user_id or current_user_id
        if not uid_str:
            return "User ID not provided."

        try:
            uid = uuid.UUID(uid_str)
            p_res = await db.execute(select(UserProgress).where(UserProgress.user_id == uid))
            progress_recs = p_res.scalars().all()

            vp_res = await db.execute(select(VideoProgress).where(VideoProgress.user_id == uid))
            video_recs = vp_res.scalars().all()

            attempts_res = await db.execute(select(AssessmentAttempt).where(AssessmentAttempt.user_id == uid))
            attempts = attempts_res.scalars().all()

            out = [
                f"Course Enrollments & Progress: {len(progress_recs)} records",
                f"Videos Watched: {len(video_recs)} videos",
                f"Assessment Attempts: {len(attempts)} attempts",
            ]
            return "\n".join(out)
        except Exception as e:
            logger.error(f"Error in get_user_learning_progress tool: {e}")
            return f"Error fetching user progress: {str(e)}"

    return [
        StructuredTool.from_function(
            coroutine=search_knowledge_base,
            name="search_knowledge_base",
            description="Search course documents, PDFs, presentations, and transcripts for relevant information.",
        ),
        StructuredTool.from_function(
            coroutine=evaluate_student_answer,
            name="evaluate_student_answer",
            description="Evaluate a student's free-form assessment answer against a rubric and correct answer.",
        ),
        StructuredTool.from_function(
            coroutine=query_course_catalog,
            name="query_course_catalog",
            description="Query available courses, learning paths, video lectures, and document assets in the LMS.",
        ),
        StructuredTool.from_function(
            coroutine=get_user_learning_progress,
            name="get_user_learning_progress",
            description="Fetch course completion status, video watch percentages, and quiz scores for a student.",
        ),
    ]
