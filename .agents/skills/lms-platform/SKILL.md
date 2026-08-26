---
name: lms-platform
description: >-
  Domain guide, developer runbook, and architectural specifications for the LMS Platform project.
  Use this skill whenever working on, debugging, testing, or building features for the lms-platform repository,
  including FastAPI backend, React (Vite) frontend, PostgreSQL + pgvector, RAG services, Google Drive auth/token management, and Docker environments.
---

# LMS Platform Developer & Architectural Skill Guide

This skill provides comprehensive instructions, architecture specs, and operational workflows for developing, debugging, maintaining, and extending the **LMS Platform** codebase.

---

## 1. Project Overview & Tech Stack

The **LMS Platform** is an end-to-end Learning Management System enhanced with a Retrieval-Augmented Generation (RAG) AI assistant, interactive assessment system, video progress tracking, and Google Drive document integration.

### Core Stack
- **Frontend**: React 19, Vite, React Router v7, Axios, Vanilla CSS design tokens (`frontend/src/index.css`).
- **Backend**: FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy 2.0 (asyncio), AsyncPG, APScheduler.
- **Database & Search**: PostgreSQL with `pgvector` extension (running on port `5433` locally via Docker), `langchain-postgres`.
- **AI & Vector Services**: LangChain, OpenAI (`gpt-4o-mini`, `text-embedding-3-small`), Ollama, LlamaParse, PyMuPDF, Unstructured PDF ingestion, YouTube transcript extractor.
- **Authentication**: JWT auth, Google OAuth2 SSO, Google Drive API (OAuth 2.0 InstalledAppFlow & token refresh).
- **Deployment & Containers**: Docker Compose (`db`, `backend`, `frontend`), Nginx configuration, Render / Netlify configs.

---

## 2. Mandatory Rules & Token Management

> [!IMPORTANT]
> **Google Drive Token Management Rule**
> Whenever the Google Drive OAuth token is invalid or expired, generate/refresh the token and overwrite `backend/token.json` and `GOOGLE_DRIVE_TOKEN` in `.env`.

### Token Refresh & Generation (`backend/generate_token.py`)
To generate or refresh Google Drive credentials:
```bash
# Run from backend/ or project root
python backend/generate_token.py
```
- First attempts a **headless refresh** using stored refresh tokens or `GOOGLE_DRIVE_TOKEN` env var.
- If headless refresh fails, launches local OAuth server on port `8085` using `oauth_client_secret.json` to complete authorization.
- Saves the output credentials to `backend/token.json` and updates `GOOGLE_DRIVE_TOKEN` in `.env`.

---

## 3. Repository Architecture & Directory Structure

```text
lms-platform/
├── GEMINI.md                    # Project-specific rules & guidelines
├── docker-compose.yml           # Local multi-container development environment
├── render.yaml                  # Deployment specification for Render
├── scripts/
│   └── ingest_data.py           # CLI tool for vectorizing PDF, URL, Wiki, & YouTube data
├── backend/
│   ├── main.py                  # FastAPI entry point & APScheduler initialization
│   ├── generate_token.py        # Google Drive token generator & auto-refresher
│   ├── oauth_client_secret.json # OAuth Client Secret for Google API
│   ├── token.json               # Active Google Drive OAuth token
│   ├── core/
│   │   ├── config.py            # Pydantic BaseSettings (.env loading & defaults)
│   │   ├── database.py          # Async engine & AsyncSessionLocal factory
│   │   └── security.py          # Password hashing & JWT helper utilities
│   ├── models/
│   │   └── db_models.py         # SQLAlchemy ORM models (Users, Courses, Modules, Lessons, Progress, Vector Store)
│   ├── routers/
│   │   ├── auth.py              # User authentication & Google SSO login
│   │   ├── admin_courses.py     # Admin course CRUD & video uploading
│   │   ├── admin_users.py       # User management & role assignment
│   │   ├── courses.py           # Student course viewing & video tracking
│   │   ├── chat.py              # RAG chatbot endpoint
│   │   ├── assessment.py        # Quiz/Assessment creation & evaluation
│   │   ├── ingest.py            # Document ingestion API endpoints
│   │   └── search.py            # Vector & semantic search API
│   └── services/
│       ├── ai_service.py        # OpenAI/Ollama LLM interaction handler
│       ├── rag_service.py       # RAG context retrieval & question answering
│       ├── google_drive_service.py # Google Drive folder scanner & downloader
│       ├── ingestion_service.py # Document parsing, chunking & vector embedding
│       ├── assessment_service.py# AI-generated quiz grading & feedback
│       └── search_service.py    # Hybrid vector + keyword search logic
└── frontend/
    ├── package.json             # React 19 & Vite dependencies
    ├── vite.config.js           # Vite dev server configuration
    ├── src/
    │   ├── App.jsx              # Main router definition & page layout wrapper
    │   ├── index.css            # Core design system tokens & theme variables
    │   ├── api/                 # Axios HTTP client configuration & endpoint services
    │   ├── components/          # Reusable UI components (Navbar, Modal, VideoPlayer, ChatWidget)
    │   └── pages/               # Application view routes (Dashboard, CourseView, AdminCourses, Assessment)
```

---

## 4. Development Environment & Setup

### Environment Configuration (`.env`)
Backend loads settings via Pydantic `backend/core/config.py`. Ensure the following keys are set:
- `DATABASE_URL`: `postgresql+asyncpg://lms_user:lms_password@localhost:5433/lms_db`
- `AI_PROVIDER`: `openai` (or `ollama`)
- `OPENAI_API_KEY`: API key for OpenAI LLM & embeddings.
- `JWT_SECRET`: Secret key for JWT session tokens.
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`: OAuth credentials for SSO.
- `GOOGLE_DRIVE_TOKEN`: Synced JSON token for Drive integration.

### Local Execution Commands

#### Option A: Docker Compose (Recommended)
```bash
docker-compose up -d --build
```
- **Database**: PostgreSQL with `pgvector` accessible at `localhost:5433`
- **Backend**: FastAPI service accessible at `http://localhost:8000` (Docs at `http://localhost:8000/docs`)
- **Frontend**: Served at `http://localhost:80` (or Vite dev port `5173` when run natively)

#### Option B: Native Execution
1. **Start PostgreSQL with Vector support**:
   ```bash
   docker run -d --name lms_pgvector -p 5433:5432 -e POSTGRES_USER=lms_user -e POSTGRES_PASSWORD=lms_password -e POSTGRES_DB=lms_db ankane/pgvector:v0.5.1
   ```
2. **Backend**:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000
   ```
3. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## 5. Key Workflows & Operations

### Data Ingestion into Vector Store
Use the CLI tool in `scripts/ingest_data.py` to index documents:
```bash
# Ingest local PDF document
python scripts/ingest_data.py --file /path/to/handout.pdf --title "Course Handout" --type pdf

# Ingest Web Article or Wikipedia page
python scripts/ingest_data.py --url "Artificial Intelligence" --type wiki --title "AI Overview"

# Ingest YouTube video transcript
python scripts/ingest_data.py --url "https://youtube.com/watch?v=xyz" --type youtube --title "Lecture Video"
```

### Database Migrations with Alembic
```bash
cd backend
# Generate migration script after model changes in models/db_models.py
alembic revision --autogenerate -m "Add new column"

# Apply pending migrations
alembic upgrade head
```

---

## 6. Verification & Quality Assurance Runbook

After making changes to backend or frontend:
1. **Check Backend API Health**:
   ```bash
   curl -f http://localhost:8000/health
   # Expected response: {"status":"ok","version":"1.0.0"}
   ```
2. **Verify Frontend Build**:
   ```bash
   cd frontend
   npm run build
   ```
3. **Validate Token Freshness**:
   If Google Drive service calls fail with `401 Unauthorized` or token errors, execute `python backend/generate_token.py`.
