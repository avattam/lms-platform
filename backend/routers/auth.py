from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
# pyrefly: ignore [missing-import]
from fastapi_sso.sso.google import GoogleSSO
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.security import create_access_token, get_current_user
from models.db_models import User
from schemas.pydantic_schemas import TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


def _get_google_sso() -> GoogleSSO:
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    if "localhost" in frontend_url and ":" not in frontend_url:
        redirect_uri = f"{frontend_url}/api/auth/google/callback"
    elif "localhost:5173" in frontend_url:
        redirect_uri = "http://localhost:8000/api/auth/google/callback"
    else:
        redirect_uri = f"{frontend_url}/api/auth/google/callback"
    print("redirect_uri", redirect_uri)
    return GoogleSSO(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        redirect_uri=redirect_uri,
        allow_insecure_http=True,
    )


async def _upsert_user(db: AsyncSession, provider: str, openid_user) -> User:
    """Find or create a user from OAuth2 provider data."""
    result = await db.execute(
        select(User).where(
            User.provider == provider,
            User.provider_user_id == str(openid_user.id),
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Check by email (user may have authenticated via a different provider)
        result = await db.execute(select(User).where(User.email == openid_user.email))
        user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=openid_user.email or "",
            full_name=openid_user.display_name,
            avatar_url=openid_user.picture,
            provider=provider,
            provider_user_id=str(openid_user.id),
        )
        db.add(user)
    else:
        user.avatar_url = openid_user.picture or user.avatar_url

    await db.commit()
    await db.refresh(user)
    return user


# ---- Google ----------------------------------------------------------------

@router.get("/google/login")
async def google_login():
    sso = _get_google_sso()
    return await sso.get_login_redirect()


@router.get("/google/callback")
async def google_callback(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    sso = _get_google_sso()
    openid_user = await sso.verify_and_process(request)
    user = await _upsert_user(db, "google", openid_user)
    token = create_access_token({"sub": str(user.id)})
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth/callback?token={token}",
        status_code=status.HTTP_302_FOUND,
    )


# ---- Current User ----------------------------------------------------------

@router.get("/me", response_model=UserOut)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.post("/logout")
async def logout():
    # JWT is stateless; client simply discards the token
    return {"message": "Logged out successfully"}
