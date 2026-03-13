"""Core application configuration."""

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ===========================================
    # Application Settings
    # ===========================================
    APP_NAME: str = "DevArchAI"
    VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development", env="ENVIRONMENT"
    )
    DEBUG: bool = Field(default=False, env="DEBUG")

    # Server
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")

    # ===========================================
    # CORS & Security
    # ===========================================
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    ALLOWED_HOSTS: list[str] = Field(
        default=["*"],
        env="ALLOWED_HOSTS"
    )
    SECRET_KEY: str = Field(default="change-me-in-production", env="SECRET_KEY")

    # ===========================================
    # Database
    # ===========================================
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/devarchai",
        env="DATABASE_URL"
    )
    DB_POOL_SIZE: int = Field(default=10, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=20, env="DB_MAX_OVERFLOW")

    # ===========================================
    # Redis & Cache
    # ===========================================
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    CACHE_TTL_SECONDS: int = Field(default=300, env="CACHE_TTL_SECONDS")

    # ===========================================
    # Celery Configuration
    # ===========================================
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_TIMEZONE: str = "UTC"
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = Field(default=30 * 60, env="CELERY_TASK_TIME_LIMIT")

    # ===========================================
    # AWS Configuration
    # ===========================================
    AWS_REGION: str = Field(default="us-east-1", env="AWS_REGION")
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    S3_BUCKET_NAME: str = Field(default="devarchai-reports", env="S3_BUCKET_NAME")
    S3_USE_CLOUDFRONT: bool = Field(default=False, env="S3_USE_CLOUDFRONT")
    CLOUDFRONT_DOMAIN: Optional[str] = Field(default=None, env="CLOUDFRONT_DOMAIN")

    # ===========================================
    # LLM Configuration
    # ===========================================
    LLM_PROVIDER: Literal["openai", "anthropic", "mock"] = Field(default="mock", env="LLM_PROVIDER")
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    LLM_MODEL: str = Field(default="gpt-4-turbo-preview", env="LLM_MODEL")
    LLM_MAX_TOKENS: int = Field(default=4096, env="LLM_MAX_TOKENS")
    LLM_TEMPERATURE: float = Field(default=0.3, env="LLM_TEMPERATURE")
    LLM_RATE_LIMIT: int = Field(default=10, env="LLM_RATE_LIMIT")  # requests per minute

    # ===========================================
    # GitHub Integration
    # ===========================================
    GITHUB_TOKEN: Optional[str] = Field(default=None, env="GITHUB_TOKEN")
    GITHUB_CLIENT_ID: Optional[str] = Field(default=None, env="GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: Optional[str] = Field(default=None, env="GITHUB_CLIENT_SECRET")
    GITHUB_WEBHOOK_SECRET: Optional[str] = Field(default=None, env="GITHUB_WEBHOOK_SECRET")

    # ===========================================
    # Analysis Settings
    # ===========================================
    MAX_REPO_SIZE_MB: int = Field(default=100, env="MAX_REPO_SIZE_MB")
    ANALYSIS_TIMEOUT_SECONDS: int = Field(default=300, env="ANALYSIS_TIMEOUT_SECONDS")
    TEMP_DIR: str = Field(default="/tmp/devarchai", env="TEMP_DIR")
    MAX_CONCURRENT_ANALYSES: int = Field(default=5, env="MAX_CONCURRENT_ANALYSES")

    # ===========================================
    # Authentication & Authorization
    # ===========================================
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    API_KEY_PREFIX: str = "dk"

    # ===========================================
    # Rate Limiting
    # ===========================================
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds
    RATE_LIMIT_AUTHENTICATED: int = Field(default=500, env="RATE_LIMIT_AUTHENTICATED")
    RATE_LIMIT_ENTERPRISE: int = Field(default=2000, env="RATE_LIMIT_ENTERPRISE")

    # ===========================================
    # Stripe Billing
    # ===========================================
    STRIPE_SECRET_KEY: Optional[str] = Field(default=None, env="STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY: Optional[str] = Field(default=None, env="STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(default=None, env="STRIPE_WEBHOOK_SECRET")
    STRIPE_PRICE_ID_PRO_MONTHLY: Optional[str] = Field(default=None, env="STRIPE_PRICE_ID_PRO_MONTHLY")
    STRIPE_PRICE_ID_ENTERPRISE_MONTHLY: Optional[str] = Field(default=None, env="STRIPE_PRICE_ID_ENTERPRISE_MONTHLY")

    # ===========================================
    # Email Configuration
    # ===========================================
    EMAIL_PROVIDER: Literal["sendgrid", "ses", "smtp"] = Field(default="smtp", env="EMAIL_PROVIDER")
    SENDGRID_API_KEY: Optional[str] = Field(default=None, env="SENDGRID_API_KEY")
    EMAIL_FROM_ADDRESS: str = Field(default="noreply@devarchai.com", env="EMAIL_FROM_ADDRESS")
    EMAIL_FROM_NAME: str = Field(default="DevArchAI", env="EMAIL_FROM_NAME")

    # SMTP settings
    SMTP_HOST: Optional[str] = Field(default=None, env="SMTP_HOST")
    SMTP_PORT: Optional[int] = Field(default=587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(default=None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")

    # ===========================================
    # Logging & Monitoring
    # ===========================================
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: Literal["json", "console"] = Field(default="json", env="LOG_FORMAT")
    LOG_REQUEST_BODY: bool = Field(default=False, env="LOG_REQUEST_BODY")

    # OpenTelemetry
    OTEL_ENABLED: bool = Field(default=False, env="OTEL_ENABLED")
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = Field(default=None, env="OTEL_EXPORTER_OTLP_ENDPOINT")
    OTEL_SERVICE_NAME: str = Field(default="devarchai-backend", env="OTEL_SERVICE_NAME")

    # ===========================================
    # Feature Flags
    # ===========================================
    FEATURE_AI_EXPLANATIONS: bool = Field(default=True, env="FEATURE_AI_EXPLANATIONS")
    FEATURE_SCHEDULED_SCANS: bool = Field(default=False, env="FEATURE_SCHEDULED_SCANS")
    FEATURE_WEBHOOKS: bool = Field(default=False, env="FEATURE_WEBHOOKS")
    FEATURE_API_KEYS: bool = Field(default=True, env="FEATURE_API_KEYS")

    # ===========================================
    # Quotas (by plan)
    # ===========================================
    QUOTA_FREE_SCANS_PER_MONTH: int = 10
    QUOTA_FREE_REPOSITORIES: int = 3
    QUOTA_FREE_TEAM_MEMBERS: int = 1
    QUOTA_FREE_REPORT_RETENTION_DAYS: int = 7

    QUOTA_PRO_SCANS_PER_MONTH: int = 100
    QUOTA_PRO_REPOSITORIES: int = 20
    QUOTA_PRO_TEAM_MEMBERS: int = 10
    QUOTA_PRO_REPORT_RETENTION_DAYS: int = 90

    QUOTA_ENTERPRISE_SCANS_PER_MONTH: int = -1  # unlimited
    QUOTA_ENTERPRISE_REPOSITORIES: int = -1
    QUOTA_ENTERPRISE_TEAM_MEMBERS: int = -1
    QUOTA_ENTERPRISE_REPORT_RETENTION_DAYS: int = 365

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v, values):
        """Warn if using default secret key in production."""
        if values.data.get('ENVIRONMENT') == 'production' and v == "change-me-in-production":
            import warnings
            warnings.warn("Using default SECRET_KEY in production is insecure!")
        return v

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

    @field_validator('ALLOWED_HOSTS', mode='before')
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from comma-separated string."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(',')]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
