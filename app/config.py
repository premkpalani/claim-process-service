from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application configuration settings"""

    # Application
    APP_NAME: str = "Claim Process Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "dev"

    # Database
    DATABASE_URL: str = "postgresql://claimuser:claimpass@db:5432/claimdb"

    # For local development with SQLite
    SQLITE_URL: str = "sqlite:///./claims.db"

    # Use PostgreSQL by default, fallback to SQLite if needed
    USE_POSTGRES: bool = True

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 10
    RATE_LIMIT_STORAGE_URL: str = "memory://"  # Use Redis in production: redis://redis:6379

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
