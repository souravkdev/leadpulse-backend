from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "LeadPulse CRM"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    # Keep SQLite as safe local fallback when DATABASE_URL is not provided.
    # Recommended runtime value is PostgreSQL via .env.
    DATABASE_URL: str = "sqlite:///./leadpulse.db"

    # JWT
    SECRET_KEY: str = "change-this-to-a-long-random-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS - comma-separated origins
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Admin seed user (created on first startup)
    FIRST_ADMIN_EMAIL: str = "admin@leadpulse.com"
    FIRST_ADMIN_PASSWORD: str = "Admin@123"
    FIRST_ADMIN_NAME: str = "System Admin"

    # Attendance
    COMPANY_TIMEZONE: str = "Asia/Kolkata"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
