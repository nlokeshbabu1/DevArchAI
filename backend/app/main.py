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

    # Validate AWS identity (fails with sys.exit(1) if running as root)
    try:
        from app.cloud.aws.sts import validate_startup_identity
        validate_startup_identity()
    except SystemExit:
        raise
    except Exception as exc:
        logger.warning(f"AWS identity check failed (non-fatal): {exc}")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Store engine reference for health checks
    from app.db.session import get_engine
    app.state.db_engine = get_engine()

    # Initialize Knowledge System (providers, cache, metrics)
    try:
        from app.knowledge.registration import initialize_knowledge_system
        knowledge_registry = await initialize_knowledge_system()
        app.state.knowledge_registry = knowledge_registry
        logger.info("Knowledge system initialized successfully")

        # Start periodic cache cleanup task
        from app.knowledge.cache import get_knowledge_cache
        cache = get_knowledge_cache()
        cache.start_cleanup_task(interval_seconds=300)
        logger.info("Knowledge cache cleanup task started")
    except Exception as e:
        logger.warning(f"Knowledge system initialization failed (non-fatal): {e}")

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

    # Start scan timeout detector (marks stuck scans as failed)
    try:
        from app.services.scan_timeout import start_timeout_detector
        await start_timeout_detector()
        logger.info("Scan timeout detector started")
    except Exception as e:
        logger.warning(f"Scan timeout detector failed to start: {e}")

    yield

    # Shutdown
    logger.info("Shutting down DevArchAI backend")

    # Cleanup knowledge cache refresh tasks
    if hasattr(app.state, 'knowledge_registry'):
        try:
            from app.knowledge.cache import get_knowledge_cache
            cache = get_knowledge_cache()
            # Stop cleanup task
            cache.stop_cleanup_task()
            # Cancel any pending refresh tasks
            for task in cache._refresh_tasks.values():
                if not task.done():
                    task.cancel()
            logger.info("Knowledge cache cleanup complete")
        except Exception as e:
            logger.warning(f"Knowledge cache cleanup failed: {e}")

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
        from app.middleware.security import (
            RateLimitMiddleware,
            SecurityHeadersMiddleware,
            SessionValidationMiddleware,
        )
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
        from fastapi import WebSocket

        from app.websockets.scan_progress import scan_progress_websocket

        @app.websocket("/ws/scan/{scan_id}")
        async def websocket_scan_progress(websocket: WebSocket, scan_id: str):
            """WebSocket endpoint for real-time scan progress updates."""
            await scan_progress_websocket(websocket, scan_id)

        logger.info("WebSocket endpoint registered at /ws/scan/{scan_id}")
    except Exception as e:
        logger.warning(f"WebSocket endpoint registration failed: {e}")

    # PHASE 2B: Add Cloud WebSocket endpoint (NEW - Production Grade)
    try:
        from fastapi import WebSocket as _WS

        from app.cloud.websocket_manager import cloud_ws_manager

        @app.websocket("/ws/cloud/{connection_id}")
        async def websocket_cloud_progress(websocket: _WS, connection_id: str):
            """WebSocket endpoint for real-time cloud scan progress updates."""
            connected = await cloud_ws_manager.connect(connection_id, websocket)
            if not connected:
                return
            try:
                while True:
                    data = await websocket.receive_text()
                    if data == "ping":
                        await websocket.send_text('{"type":"pong","data":{}}')
            except Exception:
                await cloud_ws_manager.disconnect(connection_id, websocket)

        logger.info("WebSocket endpoint registered at /ws/cloud/{connection_id}")
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
        """Readiness check - verifies database connectivity and migration state."""
        try:
            from sqlalchemy import text
            async with app.state.db_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as e:
            logger.error("Readiness check failed", error=str(e))
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=503,
                content={"status": "not ready", "database": "disconnected", "error": str(e)}
            )

        # Check migration status (sync, run in thread executor)
        import asyncio

        from app.db.migrate import current_revision, pending_migrations

        rev = await asyncio.to_thread(current_revision)
        pending = await asyncio.to_thread(pending_migrations)

        return {
            "status": "ready",
            "database": "connected",
            "migration_revision": rev,
            "pending_migrations": pending,
        }

    return app


# Create application instance
app = create_app()
