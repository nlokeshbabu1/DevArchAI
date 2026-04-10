"""
Application Configuration
"""

import secrets
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "DevArchAI"
    VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")

    # Server
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")

    # CORS
    CORS_ORIGINS: list[str] = Field(
        default_factory=list,
        env="CORS_ORIGINS",
        description="Comma-separated list or JSON array of allowed origins",
    )
    ALLOWED_HOSTS: list[str] = Field(
        default_factory=lambda: ["*"],
        env="ALLOWED_HOSTS"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from environment variable (supports comma-separated or JSON array)."""
        if v is None or v == "":
            # Default development origins
            return [
                "http://localhost",
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:5174",
                "http://127.0.0.1",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:5174",
            ]
        if isinstance(v, str):
            # Try JSON array first
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Fall back to comma-separated
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Frontend
    FRONTEND_URL: str = Field(default="http://localhost:5174", env="FRONTEND_URL")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/devarchai",
        env="DATABASE_URL"
    )
    DB_POOL_SIZE: int = Field(default=10, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=20, env="DB_MAX_OVERFLOW")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_TIMEZONE: str = "UTC"
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = Field(default=30 * 60, env="CELERY_TASK_TIME_LIMIT")

    # AWS
    AWS_REGION: str = Field(default="us-east-1", env="AWS_REGION")
    AWS_ACCESS_KEY_ID: str | None = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str | None = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    S3_BUCKET_NAME: str = Field(default="devarchai-reports", env="S3_BUCKET_NAME")

    # LLM Configuration
    LLM_PROVIDER: Literal["openai", "anthropic", "gemini", "mistral", "mock"] = Field(default="mock", env="LLM_PROVIDER")
    OPENAI_API_KEY: str | None = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str | None = Field(default=None, env="ANTHROPIC_API_KEY")
    GEMINI_API_KEY: str | None = Field(default=None, env="GEMINI_API_KEY")
    MISTRAL_API_KEY: str | None = Field(default=None, env="MISTRAL_API_KEY")
    LLM_MODEL: str = Field(default="gpt-4-turbo-preview", env="LLM_MODEL")
    LLM_MAX_TOKENS: int = Field(default=4096, env="LLM_MAX_TOKENS")
    LLM_TEMPERATURE: float = Field(default=0.3, env="LLM_TEMPERATURE")

    # GitHub
    GITHUB_TOKEN: str | None = Field(default=None, env="GITHUB_TOKEN")
    GITHUB_CLIENT_ID: str | None = Field(default=None, env="GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: str | None = Field(default=None, env="GITHUB_CLIENT_SECRET")
    GITHUB_REDIRECT_URI: str = Field(default="http://localhost:5174/auth/github/callback", env="GITHUB_REDIRECT_URI")

    # Analysis Settings
    MAX_REPO_SIZE_MB: int = Field(default=100, env="MAX_REPO_SIZE_MB")
    ANALYSIS_TIMEOUT_SECONDS: int = Field(default=300, env="ANALYSIS_TIMEOUT_SECONDS")
    TEMP_DIR: str = Field(default="/tmp/devarchai", env="TEMP_DIR")

    # Security
    SECRET_KEY: str = Field(
        default="",
        env="SECRET_KEY",
        description="CRITICAL: Must be set to a long random string in production (min 32 characters)"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")  # json, console

    # Timeouts (seconds)
    GITHUB_API_TIMEOUT: float = Field(default=10.0, env="GITHUB_API_TIMEOUT")
    GITHUB_OAUTH_TIMEOUT: float = Field(default=10.0, env="GITHUB_OAUTH_TIMEOUT")
    GIT_CLONE_TIMEOUT: int = Field(default=120, env="GIT_CLONE_TIMEOUT")
    GIT_OPERATION_TIMEOUT: int = Field(default=30, env="GIT_OPERATION_TIMEOUT")
    HTTP_REQUEST_TIMEOUT: int = Field(default=10, env="HTTP_REQUEST_TIMEOUT")
    TRIVY_TIMEOUT: int = Field(default=300, env="TRIVY_TIMEOUT")
    CHECKOV_TIMEOUT: int = Field(default=300, env="CHECKOV_TIMEOUT")
    SCAN_TIMEOUT: int = Field(default=300, env="SCAN_TIMEOUT")

    # Celery
    CELERY_RESULT_EXPIRES: int = Field(default=3600, env="CELERY_RESULT_EXPIRES")

    # Anonymous Scans
    ANONYMOUS_SCAN_EXPIRY_HOURS: int = Field(default=24, env="ANONYMOUS_SCAN_EXPIRY_HOURS")

    # ─── Payment Providers ─────────────────────────────────────────────
    STRIPE_SECRET_KEY: str | None = Field(default=None, env="STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY: str | None = Field(default=None, env="STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET: str | None = Field(default=None, env="STRIPE_WEBHOOK_SECRET")
    STRIPE_WEBHOOK_SECRET_TEST: str | None = Field(default=None, env="STRIPE_WEBHOOK_SECRET_TEST")

    RAZORPAY_KEY_ID: str | None = Field(default=None, env="RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET: str | None = Field(default=None, env="RAZORPAY_KEY_SECRET")
    RAZORPAY_WEBHOOK_SECRET: str | None = Field(default=None, env="RAZORPAY_WEBHOOK_SECRET")

    PAYPAL_CLIENT_ID: str | None = Field(default=None, env="PAYPAL_CLIENT_ID")
    PAYPAL_CLIENT_SECRET: str | None = Field(default=None, env="PAYPAL_CLIENT_SECRET")
    PAYPAL_MODE: str = Field(default="sandbox", env="PAYPAL_MODE")  # sandbox | live

    @field_validator("SECRET_KEY", mode="after")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Validate SECRET_KEY is set properly in production."""
        if not v:
            # Generate a random key for development only
            import os
            if os.environ.get("ENVIRONMENT", "development") == "development":
                return secrets.token_urlsafe(32)
            raise ValueError("SECRET_KEY must be set in production environment")
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
