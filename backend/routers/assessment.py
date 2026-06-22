"""Assessment CRUD + submission with MCQ auto-scoring and two-pass LLM grading."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.security import get_current_user, require_admin
from models.db_models import (
    AnswerRecord,
    Assessment,
    AssessmentAttempt,
    Question,
    User,
)
from schemas.pydantic_schemas import (
    AnswerFeedback,
    AssessmentIn,
    AssessmentOut,
    AttemptResultOut,
    AttemptSubmitIn,
    MessageResponse,
    QuestionIn,
    QuestionOut,
)
from services.assessment_service import grade_free_form

router = APIRouter(prefix="/assessment", tags=["Assessment"])


# ---------------------------------------------------------------------------
# Admin: Create assessment & questions
# ---------------------------------------------------------------------------

@router.post("", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    body: AssessmentIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    assessment = Assessment(**body.model_dump())
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)
    return assessment


@router.post("/{assessment_id}/questions", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
async def add_question(
    assessment_id: uuid.UUID,
    body: QuestionIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    question = Question(assessment_id=assessment_id, **body.model_dump())
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return question


# ---------------------------------------------------------------------------
# Student: Submit an attempt
# ---------------------------------------------------------------------------

@router.post("/submit", response_model=AttemptResultOut)
async def submit_attempt(
    body: AttemptSubmitIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Check attempt count (max 3)
    attempt_count = await db.scalar(
        select(func.count()).select_from(AssessmentAttempt).where(
            AssessmentAttempt.user_id == current_user.id,
            AssessmentAttempt.assessment_id == body.assessment_id,
            AssessmentAttempt.submitted_at.is_not(None),
        )
    )
    if attempt_count >= settings.MAX_ASSESSMENT_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum {settings.MAX_ASSESSMENT_ATTEMPTS} attempts reached for this assessment.",
        )

    # Load assessment + questions
    result = await db.execute(
        select(Assessment).where(Assessment.id == body.assessment_id)
    )
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    # Create attempt record
    from datetime import datetime, timezone
    attempt = AssessmentAttempt(
        user_id=current_user.id,
        assessment_id=body.assessment_id,
    )
    db.add(attempt)
    await db.flush()  # get attempt.id

    feedback: list[AnswerFeedback] = []
    total_score = 0
    max_total = 0

    for ans in body.answers:
        result = await db.execute(select(Question).where(Question.id == ans.question_id))
        question = result.scalar_one_or_none()
        if not question:
            continue

        max_total += question.max_score
        score = 0
        reasoning = None
        concepts = None

        if question.question_type == "mcq":
            # Simple exact-match scoring
            correct = next(
                (opt["text"] for opt in (question.options or []) if opt.get("is_correct")),
                None,
            )
            score = question.max_score if ans.answer == correct else 0
            reasoning = "Correct!" if score > 0 else f"The correct answer was: {correct}"

        elif question.question_type == "free_form":
            # Two-pass LLM grading
            result_grade = await grade_free_form(
                student_answer=ans.answer,
                rubric=question.rubric or "",
                correct_answer=question.correct_answer or "",
                max_score=question.max_score,
            )
            score = result_grade["score"]
            reasoning = result_grade["reasoning"]
            concepts = result_grade.get("concepts")

        total_score += score
        record = AnswerRecord(
            attempt_id=attempt.id,
            question_id=question.id,
            student_answer=ans.answer,
            score=score,
            ai_reasoning=reasoning,
            pass_1_concepts=concepts,
        )
        db.add(record)
        feedback.append(
            AnswerFeedback(
                question_id=question.id,
                score=score,
                max_score=question.max_score,
                ai_reasoning=reasoning,
            )
        )

    passed = (total_score / max_total) >= settings.PASS_THRESHOLD if max_total > 0 else False
    attempt.total_score = total_score
    attempt.passed = passed
    attempt.submitted_at = datetime.now(timezone.utc)
    await db.commit()

    return AttemptResultOut(
        attempt_id=attempt.id,
        total_score=total_score,
        max_total=max_total,
        passed=passed,
        feedback=feedback,
    )


# ---------------------------------------------------------------------------
# Student: View own attempt history
# ---------------------------------------------------------------------------

@router.get("/{assessment_id}/attempts", response_model=list[dict])
async def my_attempts(
    assessment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(AssessmentAttempt)
        .where(
            AssessmentAttempt.user_id == current_user.id,
            AssessmentAttempt.assessment_id == assessment_id,
        )
        .order_by(AssessmentAttempt.started_at.desc())
    )
    attempts = result.scalars().all()
    return [
        {
            "attempt_id": str(a.id),
            "total_score": a.total_score,
            "passed": a.passed,
            "submitted_at": a.submitted_at,
        }
        for a in attempts
    ]
