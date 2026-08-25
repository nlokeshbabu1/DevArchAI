"""
Application Configuration
"""

import logging
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

_config_logger = logging.getLogger(__name__)


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

    # Database initialization
    DB_MIGRATE_ON_STARTUP: bool = Field(default=True, env="DB_MIGRATE_ON_STARTUP")
    DB_MIGRATION_LOCK_TIMEOUT: int = Field(default=60, env="DB_MIGRATION_LOCK_TIMEOUT")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_CONNECT_TIMEOUT_SECONDS: float = Field(
        default=3.0,
        env="REDIS_CONNECT_TIMEOUT_SECONDS",
        description="Max seconds to wait when connecting to Redis at startup.",
    )
    REDIS_SOCKET_TIMEOUT_SECONDS: float = Field(
        default=3.0,
        env="REDIS_SOCKET_TIMEOUT_SECONDS",
        description="Socket read/write timeout for Redis operations.",
    )

    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_TIMEZONE: str = "UTC"
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = Field(default=30 * 60, env="CELERY_TASK_TIME_LIMIT")
    CELERY_AI_TASKS_ENABLED: bool = Field(
        default=False,
        env="CELERY_AI_TASKS_ENABLED",
        description=(
            "Route AI recommendation jobs through Celery. Default false runs AI in a "
            "background thread on the API process (required when no Celery worker is deployed)."
        ),
    )

    # AWS
    AWS_REGION: str = Field(default="us-east-1", env="AWS_REGION")
    AWS_ACCESS_KEY_ID: str | None = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str | None = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    AWS_SESSION_TOKEN: str | None = Field(default=None, env="AWS_SESSION_TOKEN")
    S3_BUCKET_NAME: str = Field(default="devarchai-reports", env="S3_BUCKET_NAME")

    # CloudFormation Template Management
    AWS_CONNECT_BUCKET: str = Field(default="devarchai-assets", env="AWS_CONNECT_BUCKET")
    AWS_CONNECT_PREFIX: str = Field(default="cloudformation", env="AWS_CONNECT_PREFIX")
    CLOUDFORMATION_TEMPLATE_VERSION: str = Field(default="v1", env="CLOUDFORMATION_TEMPLATE_VERSION")

    # DevArchAI Platform Account (constant — not customer-configurable)
    DEVARCHAI_ACCOUNT_ID: str = "961014542927"
    DEVARCHAI_SCANNER_ARN: str = Field(
        default="arn:aws:iam::961014542927:user/bedrock",
        description=(
            "ARN of the IAM entity the backend runs as. "
            "In production: arn:aws:iam::ACCOUNT:role/DevArchAIScanner (ECS/EKS task role). "
            "In dev: arn:aws:iam::ACCOUNT:user/bedrock (IAM user). "
            "The CloudFormation template trusts this ARN directly."
        ),
    )

    # LLM Configuration
    LLM_PROVIDER: Literal["openai", "anthropic", "gemini", "mistral", "ollama", "gpt4all", "mock"] = Field(
        default="mock", env="LLM_PROVIDER"
    )
    OPENAI_API_KEY: str | None = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str | None = Field(default=None, env="ANTHROPIC_API_KEY")
    GEMINI_API_KEY: str | None = Field(default=None, env="GEMINI_API_KEY")
    MISTRAL_API_KEY: str | None = Field(default=None, env="MISTRAL_API_KEY")
    MISTRAL_MODEL: str = Field(default="mistral-large-latest", env="MISTRAL_MODEL")
    LLM_MODEL: str = Field(default="gpt-4-turbo-preview", env="LLM_MODEL")
    LLM_MAX_TOKENS: int = Field(default=4096, env="LLM_MAX_TOKENS")
    LLM_TEMPERATURE: float = Field(default=0.3, env="LLM_TEMPERATURE")

    # AI suggestion generation (background flow)
    AI_CALL_TIMEOUT_SECONDS: int = Field(default=300, env="AI_CALL_TIMEOUT_SECONDS")
    AI_SUGGESTION_BATCH_SIZE: int = Field(default=5, env="AI_SUGGESTION_BATCH_SIZE")
    AI_SUGGESTION_MAX_FILE_CHARS: int = Field(default=500, env="AI_SUGGESTION_MAX_FILE_CHARS")

    # Ollama (local LLM provider)
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    OLLAMA_MODEL: str = Field(default="llama3.2", env="OLLAMA_MODEL")
    OLLAMA_TIMEOUT_SECONDS: int = Field(default=120, env="OLLAMA_TIMEOUT_SECONDS")
    OLLAMA_MAX_RETRIES: int = Field(default=2, env="OLLAMA_MAX_RETRIES")
    OLLAMA_STREAM: bool = Field(default=False, env="OLLAMA_STREAM")

    # GPT4All (local LLM provider)
    GPT4ALL_MODEL: str = Field(default="Meta-Llama-3-8B-Instruct.Q4_0.gguf", env="GPT4ALL_MODEL")
    GPT4ALL_MODEL_PATH: str | None = Field(default=None, env="GPT4ALL_MODEL_PATH")
    GPT4ALL_THREADS: int | None = Field(default=None, env="GPT4ALL_THREADS")
    GPT4ALL_MAX_TOKENS: int = Field(default=1500, env="GPT4ALL_MAX_TOKENS")

    @model_validator(mode="before")
    @classmethod
    def normalize_llm_provider_env(cls, data: Any) -> Any:
        """Accept common misconfiguration: model name set as LLM_PROVIDER on Render/etc."""
        if not isinstance(data, dict):
            return data

        raw = data.get("LLM_PROVIDER") or data.get("llm_provider")
        if not raw or not isinstance(raw, str):
            return data

        value = raw.strip()
        lowered = value.lower()

        valid_providers = {
            "openai", "anthropic", "gemini", "mistral", "ollama", "gpt4all", "mock",
        }
        if lowered in valid_providers:
            return data

        if lowered.startswith("mistral") or lowered.startswith("open-mistral"):
            if not data.get("MISTRAL_MODEL") and not data.get("mistral_model"):
                data["MISTRAL_MODEL"] = value
            data["LLM_PROVIDER"] = "mistral"
            _config_logger.warning(
                "LLM_PROVIDER was set to a Mistral model name (%r); using LLM_PROVIDER=mistral "
                "and MISTRAL_MODEL=%r. Set LLM_PROVIDER=mistral explicitly in production.",
                value,
                data["MISTRAL_MODEL"],
            )
        elif lowered.startswith("gpt-"):
            if not data.get("LLM_MODEL") and not data.get("llm_model"):
                data["LLM_MODEL"] = value
            data["LLM_PROVIDER"] = "openai"
            _config_logger.warning(
                "LLM_PROVIDER was set to an OpenAI model name (%r); using LLM_PROVIDER=openai",
                value,
            )
        elif lowered.startswith("claude"):
            if not data.get("LLM_MODEL") and not data.get("llm_model"):
                data["LLM_MODEL"] = value
            data["LLM_PROVIDER"] = "anthropic"
            _config_logger.warning(
                "LLM_PROVIDER was set to an Anthropic model name (%r); using LLM_PROVIDER=anthropic",
                value,
            )
        elif lowered.startswith("gemini"):
            if not data.get("LLM_MODEL") and not data.get("llm_model"):
                data["LLM_MODEL"] = value
            data["LLM_PROVIDER"] = "gemini"
            _config_logger.warning(
                "LLM_PROVIDER was set to a Gemini model name (%r); using LLM_PROVIDER=gemini",
                value,
            )

        return data

    # Knowledge Retrieval
    KNOWLEDGE_CACHE_TTL_SECONDS: int = Field(default=3600, env="KNOWLEDGE_CACHE_TTL_SECONDS")
    KNOWLEDGE_MAX_RESULTS_PER_PROVIDER: int = Field(default=5, env="KNOWLEDGE_MAX_RESULTS_PER_PROVIDER")
    KNOWLEDGE_ENABLED_PROVIDERS: str = Field(
        default="aws_docs,aws_pricing,aws_security,internal_rules,aws_service_quotas,aws_trusted_advisor,aws_cost_explorer",
        env="KNOWLEDGE_ENABLED_PROVIDERS",
    )
    KNOWLEDGE_LIVE_DOCS_ENABLED: bool = Field(default=False, env="KNOWLEDGE_LIVE_DOCS_ENABLED")

    # ─── RAG (Retrieval-Augmented Generation) ───────────────────────────────
    RAG_ENABLED: bool = Field(default=True, env="RAG_ENABLED")
    RAG_INVENTORY_PATH: str = Field(
        default=str(Path(__file__).resolve().parent / "rag" / "data" / "technology_inventory.yaml"),
        env="RAG_INVENTORY_PATH",
        description="Path to the technology inventory YAML (seed knowledge artifact).",
    )
    RAG_VERSION: str = Field(default="1.0.0", env="RAG_VERSION")
    RAG_CACHE_TTL_SECONDS: int = Field(default=3600, env="RAG_CACHE_TTL_SECONDS")
    RAG_MAX_RESULTS: int = Field(default=5, env="RAG_MAX_RESULTS")
    RAG_CHUNK_SIZE: int = Field(default=1200, env="RAG_CHUNK_SIZE")
    RAG_CHUNK_OVERLAP: int = Field(default=150, env="RAG_CHUNK_OVERLAP")
    RAG_SEED_ON_STARTUP: bool = Field(default=True, env="RAG_SEED_ON_STARTUP")

    # Embeddings
    EMBEDDING_PROVIDER: Literal["auto", "openai", "local"] = Field(
        default="auto", env="EMBEDDING_PROVIDER",
        description="auto=OpenAI if OPENAI_API_KEY present, else local. Override with 'openai' or 'local'.",
    )
    EMBEDDING_DIMENSION: int = Field(
        default=384, env="EMBEDDING_DIMENSION",
        description=(
            "Must match the active embedding model. Default matches "
            "all-MiniLM-L6-v2 (local). OpenAI text-embedding-3-small = 1536. "
            "This also fixes the pgvector rag_chunks.embedding column dimension, "
            "so changing it on an existing DB requires recreating that column."
        ),
    )
    EMBEDDING_LOCAL_MODEL: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_LOCAL_MODEL")
    EMBEDDING_OPENAI_MODEL: str = Field(default="text-embedding-3-small", env="EMBEDDING_OPENAI_MODEL")
    EMBEDDING_BATCH_SIZE: int = Field(default=32, env="EMBEDDING_BATCH_SIZE")
    EMBEDDING_TIMEOUT_SECONDS: int = Field(default=30, env="EMBEDDING_TIMEOUT_SECONDS")
    EMBEDDING_ALLOW_KEYWORD_FALLBACK: bool = Field(
        default=True, env="EMBEDDING_ALLOW_KEYWORD_FALLBACK",
        description="If embeddings are unavailable, retrieval falls back to keyword matching instead of failing.",
    )

    # ─── MCP / Live Context (external knowledge gateway) ────────────────────
    MCP_ENABLED: bool = Field(default=True, env="MCP_ENABLED")
    MCP_REQUEST_TIMEOUT_SECONDS: float = Field(default=10.0, env="MCP_REQUEST_TIMEOUT_SECONDS")
    MCP_MAX_RETRIES: int = Field(default=2, env="MCP_MAX_RETRIES")
    MCP_RETRY_BACKOFF_SECONDS: float = Field(default=0.5, env="MCP_RETRY_BACKOFF_SECONDS")
    MCP_CIRCUIT_BREAKER_THRESHOLD: int = Field(default=5, env="MCP_CIRCUIT_BREAKER_THRESHOLD")
    MCP_CIRCUIT_BREAKER_COOLDOWN_SECONDS: float = Field(
        default=30.0, env="MCP_CIRCUIT_BREAKER_COOLDOWN_SECONDS",
    )
    MCP_CACHE_TTL_SECONDS: int = Field(default=900, env="MCP_CACHE_TTL_SECONDS")
    MCP_LIVE_AWS_ENABLED: bool = Field(default=True, env="MCP_LIVE_AWS_ENABLED")
    MCP_LIVE_AZURE_ENABLED: bool = Field(default=True, env="MCP_LIVE_AZURE_ENABLED")
    MCP_DOCS_ENABLED: bool = Field(default=True, env="MCP_DOCS_ENABLED")

    # AI Recommendations
    AI_RECOMMENDATIONS_ENABLED: bool = Field(default=True, env="AI_RECOMMENDATIONS_ENABLED")
    AI_RECOMMENDATIONS_MAX_PER_SCAN: int = Field(default=50, env="AI_RECOMMENDATIONS_MAX_PER_SCAN")
    AI_RECOMMENDATIONS_FALLBACK_ON_LLM_FAILURE: bool = Field(
        default=True, env="AI_RECOMMENDATIONS_FALLBACK_ON_LLM_FAILURE",
    )
    # AI recommendation pipeline (async, scan-independent, cache-first).
    # Deterministic, versioned cache key components. Bump a version to
    # invalidate every cached recommendation that depended on it.
    AI_RECOMMENDATION_CACHE_TTL_SECONDS: int = Field(
        default=7 * 24 * 3600, env="AI_RECOMMENDATION_CACHE_TTL_SECONDS",
        description="TTL for LLM/rule-knowledge derived recommendations (long-lived).",
    )
    AI_RECOMMENDATION_LIVE_TTL_SECONDS: int = Field(
        default=15 * 60, env="AI_RECOMMENDATION_LIVE_TTL_SECONDS",
        description="TTL for recommendations that consumed live (MCP) context (shorter).",
    )
    AI_RECOMMENDATION_PROMPT_VERSION: str = Field(default="1.0.0", env="AI_RECOMMENDATION_PROMPT_VERSION")
    AI_RECOMMENDATION_MODEL_VERSION: str = Field(default="", env="AI_RECOMMENDATION_MODEL_VERSION")
    AI_RECOMMENDATION_LLM_TIMEOUT_SECONDS: int = Field(
        default=120, env="AI_RECOMMENDATION_LLM_TIMEOUT_SECONDS",
    )
    AI_RECOMMENDATIONS_INCLUDE_FILE_CONTEXT: bool = Field(
        default=True, env="AI_RECOMMENDATIONS_INCLUDE_FILE_CONTEXT",
        description="Include a bounded snippet of the affected file in LLM prompts (secrets redacted).",
    )
    MCP_CONTEXT_VERSION: str = Field(default="1.0.0", env="MCP_CONTEXT_VERSION")

    # GitHub
    GITHUB_TOKEN: str | None = Field(default=None, env="GITHUB_TOKEN")
    GITHUB_CLIENT_ID: str | None = Field(default=None, env="GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: str | None = Field(default=None, env="GITHUB_CLIENT_SECRET")
    GITHUB_REDIRECT_URI: str = Field(default="http://localhost:5174/auth/github/callback", env="GITHUB_REDIRECT_URI")

    # GitLab
    GITLAB_URL: str = Field(default="https://gitlab.com", env="GITLAB_URL")
    GITLAB_CLIENT_ID: str | None = Field(default=None, env="GITLAB_CLIENT_ID")
    GITLAB_CLIENT_SECRET: str | None = Field(default=None, env="GITLAB_CLIENT_SECRET")
    GITLAB_REDIRECT_URI: str = Field(default="http://localhost:5174/auth/gitlab/callback", env="GITLAB_REDIRECT_URI")
    GITLAB_SCOPE: str = Field(default="read_user api", env="GITLAB_SCOPE")

    # Jira Integration
    JIRA_API_TIMEOUT: float = Field(default=15.0, env="JIRA_API_TIMEOUT")

    # GitHub App Configuration (for SaaS platform with repo access)
    GITHUB_APP_ID: str | None = Field(default=None, env="GITHUB_APP_ID")
    GITHUB_APP_PRIVATE_KEY: str | None = Field(default=None, env="GITHUB_APP_PRIVATE_KEY")
    GITHUB_APP_PRIVATE_KEY_PATH: str | None = Field(default=None, env="GITHUB_APP_PRIVATE_KEY_PATH")
    GITHUB_APP_WEBHOOK_SECRET: str | None = Field(default=None, env="GITHUB_APP_WEBHOOK_SECRET")
    GITHUB_APP_SLUG: str | None = Field(default=None, env="GITHUB_APP_SLUG")

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
    ENCRYPTION_KEY: str | None = Field(
        default=None,
        env="ENCRYPTION_KEY",
        description="Optional Fernet-compatible key for encryption. If not set, derived from SECRET_KEY (less stable)."
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds
    RATE_LIMIT_AUTH_REQUESTS: int = Field(default=10, env="RATE_LIMIT_AUTH_REQUESTS")  # stricter for auth endpoints
    RATE_LIMIT_AUTH_WINDOW: int = Field(default=60, env="RATE_LIMIT_AUTH_WINDOW")  # seconds

    # Refresh Token Storage Mode
    AUTH_REFRESH_TOKEN_STORAGE_MODE: Literal["legacy", "hybrid", "cookie_only"] = Field(
        default="hybrid", env="AUTH_REFRESH_TOKEN_STORAGE_MODE",
        description="legacy=localStorage only, hybrid=cookie+localStorage, cookie_only=cookie only"
    )

    # Account Lockout
    MAX_FAILED_LOGIN_ATTEMPTS: int = Field(default=5, env="MAX_FAILED_LOGIN_ATTEMPTS")
    ACCOUNT_LOCKOUT_MINUTES: int = Field(default=15, env="ACCOUNT_LOCKOUT_MINUTES")

    # Cookie Security
    COOKIE_SECURE: bool = Field(default=False, env="COOKIE_SECURE")
    COOKIE_SAMESITE: str = Field(default="Strict", env="COOKIE_SAMESITE")
    COOKIE_DOMAIN: str | None = Field(default=None, env="COOKIE_DOMAIN")
    COOKIE_PATH: str = Field(default="/", env="COOKIE_PATH")

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
        #env_file = ".env"
        env_file = str(Path(__file__).resolve().parents[1] / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
