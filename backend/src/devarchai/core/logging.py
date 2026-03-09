"""Logging configuration using structlog."""

import logging
import sys
from typing import Any, Dict
import structlog
from structlog.types import Processor

from devarchai.config import settings


def setup_logging() -> None:
    """Configure logging and structlog."""
    
    # Determine log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure logging handlers
    if settings.LOG_FORMAT == "json":
        # JSON format for production
        processors: list[Processor] = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Console format for development
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """Get a logger instance."""
    return structlog.get_logger(name)


class LoggingMiddleware:
    """Middleware for logging requests and responses."""

    def __init__(self, app):
        self.app = app
        self.logger = get_logger("request")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        # Extract request info
        method = scope["method"]
        path = scope["path"]
        
        self.logger.info(
            "request_started",
            method=method,
            path=path,
        )

        # Track response status
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status = message["status"]
                self.logger.info(
                    "request_completed",
                    method=method,
                    path=path,
                    status_code=status,
                )
            await send(message)

        return await self.app(scope, receive, send_wrapper)
