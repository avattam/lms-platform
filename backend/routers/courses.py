"""Student-facing course and video endpoints — filtered by active enrollment."""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from models.db_models import Course, CourseDocument, CourseVideo, CourseViewLog, User, UserEnrollment, VideoProgress
from schemas.pydantic_schemas import (
    CourseOut,
    CourseDocumentOut,
    MessageResponse,
    SessionEndIn,
    SessionStartOut,
    VideoOut,
    VideoProgressIn,
    VideoProgressOut,
)

router = APIRouter(prefix="/courses", tags=["Courses"])
video_router = APIRouter(prefix="/video", tags=["Video Progress"])


# ---------------------------------------------------------------------------
# Helper: assert student is enrolled
# ---------------------------------------------------------------------------
async def _assert_enrolled(user: User, course_id: uuid.UUID, db: AsyncSession):
    if user.role == "admin":
        return
    result = await db.execute(
        select(UserEnrollment).where(
            UserEnrollment.user_id == user.id,
            UserEnrollment.course_id == course_id,
            UserEnrollment.removed_at.is_(None),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enrolled in this course.")


# ===========================================================================
# Course listing (student sees only enrolled, published courses)
# ===========================================================================

@router.get("", response_model=list[CourseOut])
async def list_my_courses(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(Course)
        .join(UserEnrollment, UserEnrollment.course_id == Course.id)
        .where(
            UserEnrollment.user_id == current_user.id,
            UserEnrollment.removed_at.is_(None),
            Course.is_published == True,
        )
        .order_by(Course.sequence_order)
    )
    return result.scalars().all()


@router.get("/{course_id}", response_model=CourseOut)
async def get_course(
    course_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    await _assert_enrolled(current_user, course_id, db)
    query = select(Course).where(Course.id == course_id)
    if current_user.role != "admin":
        query = query.where(Course.is_published == True)
    result = await db.execute(query)
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    return course


@router.get("/{course_id}/videos", response_model=list[VideoOut])
async def list_course_videos(
    course_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    await _assert_enrolled(current_user, course_id, db)
    query = select(CourseVideo).where(CourseVideo.course_id == course_id)
    # if current_user.role != "admin":
    #     query = query.where(CourseVideo.is_published == True)
    result = await db.execute(query.order_by(CourseVideo.sequence_order))
    return result.scalars().all()


@router.get("/{course_id}/documents", response_model=list[CourseDocumentOut])
async def list_student_course_documents(
    course_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    await _assert_enrolled(current_user, course_id, db)
    query = select(Course).where(Course.id == course_id)
    if current_user.role != "admin":
        query = query.where(Course.is_published == True)
    result = await db.execute(query)
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    res = await db.execute(
        select(CourseDocument)
        .where(CourseDocument.course_id == course_id)
        .order_by(CourseDocument.uploaded_at.desc())
    )
    return res.scalars().all()


# ===========================================================================
# Video Progress (resume from last position)
# ===========================================================================

@video_router.get("/{video_id}/progress", response_model=VideoProgressOut)
async def get_video_progress(
    video_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(VideoProgress).where(
            VideoProgress.user_id == current_user.id,
            VideoProgress.video_id == video_id,
        )
    )
    progress = result.scalar_one_or_none()
    if not progress:
        # No record yet — start from the beginning
        return VideoProgressOut(
            last_position_secs=0,
            watch_percent=0.0,
            completed=False,
            last_watched_at=datetime.now(timezone.utc),
        )
    return progress


@video_router.patch("/{video_id}/progress", response_model=MessageResponse)
async def save_video_progress(
    video_id: uuid.UUID,
    body: VideoProgressIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Heartbeat endpoint — called every 10 seconds by the player."""
    result = await db.execute(
        select(VideoProgress).where(
            VideoProgress.user_id == current_user.id,
            VideoProgress.video_id == video_id,
        )
    )
    progress = result.scalar_one_or_none()

    if progress:
        progress.last_position_secs = body.position_secs
        progress.watch_percent = body.watch_percent
        progress.completed = body.completed
        progress.last_watched_at = datetime.now(timezone.utc)
    else:
        progress = VideoProgress(
            user_id=current_user.id,
            video_id=video_id,
            last_position_secs=body.position_secs,
            watch_percent=body.watch_percent,
            completed=body.completed,
        )
        db.add(progress)

    await db.commit()
    return {"message": "Progress saved."}


# ===========================================================================
# View Session (Audit Log)
# ===========================================================================

@video_router.post("/{video_id}/session/start", response_model=SessionStartOut, status_code=status.HTTP_201_CREATED)
async def start_view_session(
    video_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Lookup video to get course_id
    result = await db.execute(select(CourseVideo).where(CourseVideo.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    log = CourseViewLog(
        user_id=current_user.id,
        course_id=video.course_id,
        video_id=video_id,
        device_info=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return {"session_id": log.id}


@video_router.post("/{video_id}/session/end", response_model=MessageResponse)
async def end_view_session(
    video_id: uuid.UUID,
    body: SessionEndIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(CourseViewLog).where(CourseViewLog.id == body.session_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    now = datetime.now(timezone.utc)
    log.session_end = now
    log.duration_secs = int((now - log.session_start.replace(tzinfo=timezone.utc)).total_seconds())
    await db.commit()
    return {"message": "Session ended."}
