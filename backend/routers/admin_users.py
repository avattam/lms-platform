"""Admin: User management — activate/deactivate users, manage course enrollments."""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import require_admin
from models.db_models import Course, User, UserEnrollment
from schemas.pydantic_schemas import (
    EnrollmentIn,
    EnrollmentOut,
    MessageResponse,
    UserCreate,
    UserListOut,
    UserOut,
    UserUpdate,
)

router = APIRouter(prefix="/admin/users", tags=["Admin — Users"])


# ---------------------------------------------------------------------------
# List all users
# ---------------------------------------------------------------------------
@router.get("", response_model=list[UserListOut])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
    search: str | None = Query(None, description="Filter by name or email"),
    role: str | None = Query(None, description="Filter by role: admin | student"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    skip: int = 0,
    limit: int = 50,
):
    stmt = select(User)
    if search:
        stmt = stmt.where(
            User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        )
    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    stmt = stmt.offset(skip).limit(limit).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Get single user profile + enrollment summary
# ---------------------------------------------------------------------------
@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# ---------------------------------------------------------------------------
# Activate a user
# ---------------------------------------------------------------------------
@router.patch("/{user_id}/activate", response_model=MessageResponse)
async def activate_user(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = True
    user.deactivated_at = None
    user.deactivated_by = None
    await db.commit()
    return {"message": f"User {user.email} has been activated."}


# ---------------------------------------------------------------------------
# Deactivate a user
# ---------------------------------------------------------------------------
@router.patch("/{user_id}/deactivate", response_model=MessageResponse)
async def deactivate_user(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself.")

    user.is_active = False
    user.deactivated_at = datetime.now(timezone.utc)
    user.deactivated_by = admin.id
    await db.commit()
    return {"message": f"User {user.email} has been deactivated."}


# ---------------------------------------------------------------------------
# List enrollments for a user
# ---------------------------------------------------------------------------
@router.get("/{user_id}/enrollments", response_model=list[EnrollmentOut])
async def list_user_enrollments(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
    active_only: bool = Query(True),
):
    stmt = select(UserEnrollment).where(UserEnrollment.user_id == user_id)
    if active_only:
        stmt = stmt.where(UserEnrollment.removed_at.is_(None))
    result = await db.execute(stmt)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Enroll a user in a course
# ---------------------------------------------------------------------------
@router.post("/{user_id}/enrollments", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED)
async def enroll_user(
    user_id: uuid.UUID,
    body: EnrollmentIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    # Validate user exists
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Validate course exists and is published
    result = await db.execute(select(Course).where(Course.id == body.course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # Check for existing active enrollment
    result = await db.execute(
        select(UserEnrollment).where(
            UserEnrollment.user_id == user_id,
            UserEnrollment.course_id == body.course_id,
            UserEnrollment.removed_at.is_(None),
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already enrolled in this course.")

    enrollment = UserEnrollment(
        user_id=user_id,
        course_id=body.course_id,
        enrolled_by=admin.id,
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


# ---------------------------------------------------------------------------
# Remove a user from a course (soft-delete)
# ---------------------------------------------------------------------------
@router.delete("/{user_id}/enrollments/{course_id}", response_model=MessageResponse)
async def remove_enrollment(
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(
        select(UserEnrollment).where(
            UserEnrollment.user_id == user_id,
            UserEnrollment.course_id == course_id,
            UserEnrollment.removed_at.is_(None),
        )
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active enrollment not found.")

    enrollment.removed_at = datetime.now(timezone.utc)
    enrollment.removed_by = admin.id
    await db.commit()
    return {"message": "Enrollment removed successfully."}


# ---------------------------------------------------------------------------
# Create a user
# ---------------------------------------------------------------------------
@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    # Check if user with email already exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists."
        )

    provider_user_id = body.provider_user_id or str(uuid.uuid4())
    user = User(
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        is_active=body.is_active,
        provider=body.provider,
        provider_user_id=provider_user_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Update a user
# ---------------------------------------------------------------------------
@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # If email is being changed, verify uniqueness
    if body.email is not None and body.email != user.email:
        email_check = await db.execute(select(User).where(User.email == body.email))
        if email_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists."
            )
        user.email = body.email

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None and body.is_active != user.is_active:
        user.is_active = body.is_active
        if not body.is_active:
            user.deactivated_at = datetime.now(timezone.utc)
            user.deactivated_by = admin.id
        else:
            user.deactivated_at = None
            user.deactivated_by = None

    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Delete a user
# ---------------------------------------------------------------------------
@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself."
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        await db.delete(user)
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete user. This user has associated records (e.g. uploaded assets, created courses)."
        )
    return {"message": f"User {user.email} has been deleted."}
