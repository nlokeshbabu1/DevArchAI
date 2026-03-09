"""
DevArchAI - AI-Powered DevOps Production Readiness Engine
Backend Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import structlog

from app.config import settings
from app.api.v1.router import api_router
from app.core.exceptions import setup_exception_handlers
from app.core.logging import setup_logging
from app.db.session import init_db, close_db

# Setup structured logging
setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting DevArchAI backend", version=settings.VERSION, environment=settings.ENVIRONMENT)

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down DevArchAI backend")
    await close_db()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title="DevArchAI API",
        description="AI-Powered DevOps Production Readiness Engine",
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security middleware for production
    if settings.ENVIRONMENT == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS,
        )

    # Setup exception handlers
    setup_exception_handlers(app)

    # Include API v1 router
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/")
    async def root():
        return {
            "name": "DevArchAI",
            "version": settings.VERSION,
            "status": "running",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    @app.get("/health")
    async def root_health():
        """Root health check for load balancers."""
        return {"status": "healthy"}

    return app


# Create application instance
app = create_app()
