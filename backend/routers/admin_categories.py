import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user, require_admin
from models.db_models import Course, CourseCategory, CourseCategoryAssociation, User
from schemas.pydantic_schemas import (
    CategoryCourseAssignResponse,
    CategoryCourseItem,
    CategoryCourseSync,
    CategoryIn,
    CategoryOut,
    CategoryUpdate,
    CategoryWithCoursesOut,
    MessageResponse,
)

router = APIRouter(prefix="/admin/categories", tags=["Admin — Course Categories"])
public_router = APIRouter(prefix="/categories", tags=["Course Categories"])


def generate_slug(name: str) -> str:
    """Generate a clean URL-friendly slug from category name."""
    s = name.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    s = s.strip("-")
    return s or "category"


# ===========================================================================
# Admin Endpoints
# ===========================================================================

@router.get("", response_model=list[CategoryOut])
async def list_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    """List all categories with their associated course counts."""
    # Subquery / join to count courses per category
    stmt = (
        select(
            CourseCategory,
            func.count(CourseCategoryAssociation.id).label("course_count"),
        )
        .outerjoin(
            CourseCategoryAssociation,
            CourseCategory.id == CourseCategoryAssociation.category_id,
        )
        .group_by(CourseCategory.id)
        .order_by(CourseCategory.name.asc())
    )
    result = await db.execute(stmt)
    categories = []
    for cat, count in result.all():
        cat_out = CategoryOut(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            description=cat.description,
            icon=cat.icon,
            color=cat.color,
            course_count=count,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
        )
        categories.append(cat_out)
    return categories


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    """Create a new category with duplicate name checks and slug generation."""
    clean_name = body.name.strip()
    if not clean_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Category name cannot be empty.",
        )

    # Check case-insensitive duplicate name
    dup = await db.execute(
        select(CourseCategory).where(func.lower(CourseCategory.name) == clean_name.lower())
    )
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category with name '{clean_name}' already exists.",
        )

    # Base slug & ensure uniqueness if collided
    base_slug = generate_slug(clean_name)
    slug = base_slug
    counter = 1
    while True:
        existing_slug = await db.execute(
            select(CourseCategory).where(CourseCategory.slug == slug)
        )
        if not existing_slug.scalar_one_or_none():
            break
        counter += 1
        slug = f"{base_slug}-{counter}"

    category = CourseCategory(
        name=clean_name,
        slug=slug,
        description=body.description.strip() if body.description else None,
        icon=body.icon or "🏷️",
        color=body.color or "#6366f1",
        created_by=admin.id,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)

    return CategoryOut(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        icon=category.icon,
        color=category.color,
        course_count=0,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


@router.get("/{category_id}", response_model=CategoryWithCoursesOut)
async def get_category_with_courses(
    category_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    """Get category details along with all assigned courses."""
    cat_res = await db.execute(
        select(CourseCategory).where(CourseCategory.id == category_id)
    )
    category = cat_res.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    # Fetch assigned courses
    stmt = (
        select(Course, CourseCategoryAssociation.assigned_at)
        .join(
            CourseCategoryAssociation,
            CourseCategoryAssociation.course_id == Course.id,
        )
        .where(CourseCategoryAssociation.category_id == category_id)
        .order_by(Course.title.asc())
    )
    result = await db.execute(stmt)
    courses_list = []
    for course, assigned_at in result.all():
        courses_list.append(
            CategoryCourseItem(
                id=course.id,
                title=course.title,
                description=course.description,
                is_published=course.is_published,
                assigned_at=assigned_at,
            )
        )

    return CategoryWithCoursesOut(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        icon=category.icon,
        color=category.color,
        course_count=len(courses_list),
        created_at=category.created_at,
        updated_at=category.updated_at,
        courses=courses_list,
    )


@router.put("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: uuid.UUID,
    body: CategoryUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    """Update category name, description, icon, or color."""
    cat_res = await db.execute(
        select(CourseCategory).where(CourseCategory.id == category_id)
    )
    category = cat_res.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    if body.name is not None:
        clean_name = body.name.strip()
        if not clean_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Category name cannot be empty.",
            )
        # Check duplicate name on other categories
        dup = await db.execute(
            select(CourseCategory).where(
                func.lower(CourseCategory.name) == clean_name.lower(),
                CourseCategory.id != category_id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Category with name '{clean_name}' already exists.",
            )
        category.name = clean_name
        category.slug = generate_slug(clean_name)

    if body.description is not None:
        category.description = body.description.strip() if body.description else None
    if body.icon is not None:
        category.icon = body.icon or "🏷️"
    if body.color is not None:
        category.color = body.color or "#6366f1"

    await db.commit()
    await db.refresh(category)

    # Count courses
    count_res = await db.execute(
        select(func.count(CourseCategoryAssociation.id)).where(
            CourseCategoryAssociation.category_id == category.id
        )
    )
    course_count = count_res.scalar() or 0

    return CategoryOut(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        icon=category.icon,
        color=category.color,
        course_count=course_count,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


@router.delete("/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    """Safely delete a category without affecting assigned course records."""
    cat_res = await db.execute(
        select(CourseCategory).where(CourseCategory.id == category_id)
    )
    category = cat_res.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    await db.delete(category)
    await db.commit()
    return {"message": "Category deleted successfully."}


@router.post("/{category_id}/courses", response_model=CategoryCourseAssignResponse)
async def sync_category_courses(
    category_id: uuid.UUID,
    body: CategoryCourseSync,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    """Batch sync or assign courses to a category."""
    cat_res = await db.execute(
        select(CourseCategory).where(CourseCategory.id == category_id)
    )
    category = cat_res.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    # Validate courses exist
    target_ids = set(body.course_ids)
    if target_ids:
        courses_res = await db.execute(
            select(Course.id).where(Course.id.in_(target_ids))
        )
        found_ids = set(courses_res.scalars().all())
        missing_ids = target_ids - found_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Some courses were not found: {list(missing_ids)}",
            )

    # Get current associations
    existing_assoc_res = await db.execute(
        select(CourseCategoryAssociation).where(
            CourseCategoryAssociation.category_id == category_id
        )
    )
    existing_associations = existing_assoc_res.scalars().all()
    existing_course_ids = {assoc.course_id for assoc in existing_associations}

    # Delete unselected associations
    to_delete = [
        assoc for assoc in existing_associations if assoc.course_id not in target_ids
    ]
    for assoc in to_delete:
        await db.delete(assoc)

    # Insert newly selected associations
    to_add_ids = target_ids - existing_course_ids
    for c_id in to_add_ids:
        new_assoc = CourseCategoryAssociation(
            category_id=category_id,
            course_id=c_id,
            assigned_by=admin.id,
        )
        db.add(new_assoc)

    await db.commit()

    return {
        "message": "Course assignments updated successfully.",
        "assigned_count": len(target_ids),
    }


@router.delete("/{category_id}/courses/{course_id}", response_model=MessageResponse)
async def remove_course_from_category(
    category_id: uuid.UUID,
    course_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
):
    """Remove a single course association from a category."""
    assoc_res = await db.execute(
        select(CourseCategoryAssociation).where(
            CourseCategoryAssociation.category_id == category_id,
            CourseCategoryAssociation.course_id == course_id,
        )
    )
    assoc = assoc_res.scalar_one_or_none()
    if not assoc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course is not assigned to this category.",
        )

    await db.delete(assoc)
    await db.commit()
    return {"message": "Course removed from category."}


# ===========================================================================
# Public / Student Endpoint
# ===========================================================================

@public_router.get("", response_model=list[CategoryOut])
async def list_public_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User | None, Depends(get_current_user)] = None,
):
    """List categories available for course discovery."""
    stmt = (
        select(
            CourseCategory,
            func.count(CourseCategoryAssociation.id).label("course_count"),
        )
        .outerjoin(
            CourseCategoryAssociation,
            CourseCategory.id == CourseCategoryAssociation.category_id,
        )
        .group_by(CourseCategory.id)
        .order_by(CourseCategory.name.asc())
    )
    result = await db.execute(stmt)
    categories = []
    for cat, count in result.all():
        categories.append(
            CategoryOut(
                id=cat.id,
                name=cat.name,
                slug=cat.slug,
                description=cat.description,
                icon=cat.icon,
                color=cat.color,
                course_count=count,
                created_at=cat.created_at,
                updated_at=cat.updated_at,
            )
        )
    return categories
