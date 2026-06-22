"""FastAPI main application entry point."""
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import engine
from models import db_models  # noqa: F401 — ensure all models are registered
from routers import admin_courses, admin_users, assessment, auth, chat, courses, ingest, search
from routers.courses import video_router


# ---------------------------------------------------------------------------
# APScheduler: cleanup orphaned view sessions
# ---------------------------------------------------------------------------
async def cleanup_orphaned_sessions():
    """Set session_end for view logs that were never closed (browser crash etc.)."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import update
    from core.database import AsyncSessionLocal
    from models.db_models import CourseViewLog

    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.SESSION_TIMEOUT_HOURS)
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(CourseViewLog)
            .where(
                CourseViewLog.session_end.is_(None),
                CourseViewLog.session_start < cutoff,
            )
            .values(session_end=cutoff)
        )
        await db.commit()


scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start nightly cleanup job
    scheduler.add_job(cleanup_orphaned_sessions, "cron", hour=2, minute=0)
    scheduler.start()
    yield
    scheduler.shutdown()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="RAG-Based LMS API",
    description="Learning Management System with RAG chatbot, hybrid assessment, and video tracking.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth.router)
app.include_router(admin_users.router)
app.include_router(admin_courses.router)
app.include_router(courses.router)
app.include_router(video_router)
app.include_router(chat.router)
app.include_router(assessment.router)
app.include_router(ingest.router)
app.include_router(search.router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
