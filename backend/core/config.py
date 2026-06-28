from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://lms_user:lms_password@localhost:5433/lms_db"

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours

    # OAuth2 providers
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Google Drive Documents
    GOOGLE_DRIVE_CREDENTIALS_FILE: str = "gdrive.json"
    GOOGLE_DRIVE_TOKEN_FILE: str = "token.json"
    GOOGLE_DRIVE_FOLDER_ID: str = "17QW0i_zyZRvXJwb-4IaOpbOHCO0lMbUT"

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11435"
    LLM_MODEL: str = "qwen3:1.7b"
    EMBED_MODEL: str = "nomic-embed-text"

    # App
    APP_BASE_URL: str = "http://backend:8000"
    FRONTEND_URL: str = "http://localhost"
    CORS_ORIGINS: list[str] = ["http://localhost"]

    # Assessment
    PASS_THRESHOLD: float = 0.60  # 60%
    MAX_ASSESSMENT_ATTEMPTS: int = 3

    # Video Progress
    HEARTBEAT_INTERVAL_SECS: int = 10
    SESSION_TIMEOUT_HOURS: int = 2  # cleanup orphaned sessions after this


settings = Settings()
