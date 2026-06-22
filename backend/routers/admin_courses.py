"""Admin: Course, video, and learning path management."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import require_admin
from models.db_models import Course, CourseVideo, CourseViewLog, LearningPath, User
from schemas.pydantic_schemas import (
    CourseIn,
    CourseOut,
    CourseUpdate,
    LearningPathIn,
    LearningPathOut,
    MessageResponse,
    VideoIn,
    VideoOut,
    VideoUpdate,
    ViewLogOut,
)

router = APIRouter(prefix="/admin", tags=["Admin — Courses"])


# ===========================================================================
# Learning Paths
# ===========================================================================

@router.post("/paths", response_model=LearningPathOut, status_code=status.HTTP_201_CREATED)
async def create_path(
    body: LearningPathIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    path = LearningPath(**body.model_dump(), created_by=admin.id)
    db.add(path)
    await db.commit()
    await db.refresh(path)
    return path


@router.get("/paths", response_model=list[LearningPathOut])
async def list_paths(
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(LearningPath).order_by(LearningPath.created_at))
    return result.scalars().all()


@router.put("/paths/{path_id}", response_model=LearningPathOut)
async def update_path(
    path_id: uuid.UUID,
    body: LearningPathIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(LearningPath).where(LearningPath.id == path_id))
    path = result.scalar_one_or_none()
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(path, k, v)
    await db.commit()
    await db.refresh(path)
    return path


@router.delete("/paths/{path_id}", response_model=MessageResponse)
async def delete_path(
    path_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(LearningPath).where(LearningPath.id == path_id))
    path = result.scalar_one_or_none()
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")
    await db.delete(path)
    await db.commit()
    return {"message": "Learning path deleted."}


# ===========================================================================
# Courses
# ===========================================================================

@router.post("/courses", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
async def create_course(
    body: CourseIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    course = Course(**body.model_dump(), created_by=admin.id)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


@router.get("/courses", response_model=list[CourseOut])
async def list_courses(
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
    path_id: uuid.UUID | None = Query(None),
):
    stmt = select(Course).order_by(Course.sequence_order)
    if path_id:
        stmt = stmt.where(Course.path_id == path_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.put("/courses/{course_id}", response_model=CourseOut)
async def update_course(
    course_id: uuid.UUID,
    body: CourseUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(course, k, v)
    await db.commit()
    await db.refresh(course)
    return course


@router.delete("/courses/{course_id}", response_model=MessageResponse)
async def delete_course(
    course_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    await db.delete(course)
    await db.commit()
    return {"message": "Course deleted."}


@router.patch("/courses/{course_id}/publish", response_model=CourseOut)
async def toggle_publish_course(
    course_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    course.is_published = not course.is_published
    await db.commit()
    await db.refresh(course)
    return course


# ===========================================================================
# Videos
# ===========================================================================

@router.post("/courses/{course_id}/videos", response_model=VideoOut, status_code=status.HTTP_201_CREATED)
async def add_video(
    course_id: uuid.UUID,
    body: VideoIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    video = CourseVideo(course_id=course_id, **body.model_dump())
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video


@router.put("/videos/{video_id}", response_model=VideoOut)
async def update_video(
    video_id: uuid.UUID,
    body: VideoUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(CourseVideo).where(CourseVideo.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(video, k, v)
    await db.commit()
    await db.refresh(video)
    return video


@router.delete("/videos/{video_id}", response_model=MessageResponse)
async def delete_video(
    video_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(CourseVideo).where(CourseVideo.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    await db.delete(video)
    await db.commit()
    return {"message": "Video deleted."}


@router.patch("/videos/{video_id}/publish", response_model=VideoOut)
async def toggle_publish_video(
    video_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(CourseVideo).where(CourseVideo.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    video.is_published = not video.is_published
    await db.commit()
    await db.refresh(video)
    return video


# ===========================================================================
# Audit Log
# ===========================================================================

@router.get("/logs/views", response_model=list[ViewLogOut])
async def get_view_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
    user_id: uuid.UUID | None = Query(None),
    course_id: uuid.UUID | None = Query(None),
    skip: int = 0,
    limit: int = 100,
):
    stmt = select(CourseViewLog).order_by(CourseViewLog.session_start.desc())
    if user_id:
        stmt = stmt.where(CourseViewLog.user_id == user_id)
    if course_id:
        stmt = stmt.where(CourseViewLog.course_id == course_id)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/logs/users/{user_id}", response_model=list[ViewLogOut])
async def get_user_view_logs(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
    skip: int = 0,
    limit: int = 100,
):
    result = await db.execute(
        select(CourseViewLog)
        .where(CourseViewLog.user_id == user_id)
        .order_by(CourseViewLog.session_start.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
