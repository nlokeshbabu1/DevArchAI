"""
DevArchAI - AI-Powered DevOps Production Readiness Engine
Backend Application Entry Point
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import api_router
from app.api.v1.routes.billing import create_checkout_session, get_billing_gateway, verify_payment
from app.config import settings
from app.core.exceptions import setup_exception_handlers
from app.core.logging import setup_logging
from app.db.session import close_db, init_db

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

    # Store engine reference for health checks
    from app.db.session import get_engine
    app.state.db_engine = get_engine()

    # PHASE 2C: Initialize Redis cache (NEW - Production Grade)
    try:
        from app.cache import get_cache
        cache = await get_cache()
        if cache and cache.is_connected:
            logger.info("Redis cache initialized successfully")
            app.state.cache = cache
        else:
            logger.warning("Redis cache not available, continuing without caching")
    except Exception as e:
        logger.warning(f"Redis cache initialization failed: {e}")

    # PHASE 2B: Initialize WebSocket manager (NEW - Production Grade)
    try:
        from app.websockets.scan_progress import ScanProgressWebSocketManager
        app.state.ws_manager = ScanProgressWebSocketManager()
        logger.info("WebSocket manager initialized")
    except Exception as e:
        logger.warning(f"WebSocket manager initialization failed: {e}")

    yield

    # Shutdown
    logger.info("Shutting down DevArchAI backend")
    
    # Close Redis connection
    if hasattr(app.state, 'cache'):
        try:
            await app.state.cache.close()
            logger.info("Redis cache closed")
        except Exception as e:
            logger.warning(f"Error closing Redis cache: {e}")
    
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

    # PHASE 6: Add error tracking and request logging middleware (NEW - Observability)
    try:
        from app.middleware.error_tracking import ErrorTrackingMiddleware, RequestLoggingMiddleware
        app.add_middleware(RequestLoggingMiddleware)
        app.add_middleware(ErrorTrackingMiddleware)
        logger.info("Error tracking and request logging middleware enabled")
    except Exception as e:
        logger.warning(f"Error tracking middleware registration failed: {e}")

    # Enterprise Security Middleware
    try:
        from app.middleware.security import SecurityHeadersMiddleware, RateLimitMiddleware, SessionValidationMiddleware
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(RateLimitMiddleware)
        app.add_middleware(SessionValidationMiddleware)
        logger.info("Security headers, rate limiting, and session validation middleware enabled")
    except Exception as e:
        logger.warning(f"Security middleware registration failed: {e}")

    # Setup exception handlers
    setup_exception_handlers(app)

    # Include API v1 router
    app.include_router(api_router, prefix="/api/v1")
    app.add_api_route("/api/payment/checkout", create_checkout_session, methods=["POST"], response_model=dict)
    app.add_api_route("/api/payment/gateway", get_billing_gateway, methods=["GET"], response_model=dict)
    app.add_api_route("/api/payment/verify", verify_payment, methods=["POST"], response_model=dict)

    # PHASE 6: Add Prometheus metrics endpoint (NEW - Observability)
    try:
        from app.services.metrics import router as metrics_router
        app.include_router(metrics_router)
        logger.info("Prometheus metrics endpoint registered at /metrics")
    except Exception as e:
        logger.warning(f"Metrics endpoint registration failed: {e}")

    # PHASE 2B: Add WebSocket endpoint (NEW - Production Grade)
    try:
        from app.websockets.scan_progress import scan_progress_websocket
        from fastapi import WebSocket

        @app.websocket("/ws/scan/{scan_id}")
        async def websocket_scan_progress(websocket: WebSocket, scan_id: str):
            """WebSocket endpoint for real-time scan progress updates."""
            await scan_progress_websocket(websocket, scan_id)
        
        logger.info("WebSocket endpoint registered at /ws/scan/{scan_id}")
    except Exception as e:
        logger.warning(f"WebSocket endpoint registration failed: {e}")

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

    @app.get("/api/v1/ready")
    async def readiness_check():
        """Readiness check - verifies database connectivity."""
        try:
            from sqlalchemy import text
            async with app.state.db_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return {"status": "ready", "database": "connected"}
        except Exception as e:
            logger.error("Readiness check failed", error=str(e))
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=503,
                content={"status": "not ready", "database": "disconnected", "error": str(e)}
            )

    return app


# Create application instance
app = create_app()
