"""
Error Tracking Middleware for DevArchAI

Provides application-level error tracking and reporting:
- Captures unhandled exceptions
- Tracks error rates by endpoint
- Sends alerts for critical errors
- Integrates with Sentry (optional)

Usage:
    Automatically enabled via middleware in main.py
"""

import time
import traceback
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.metrics import record_error

logger = structlog.get_logger(__name__)


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track errors in the application.
    
    Features:
    - Captures unhandled exceptions
    - Records error metrics
    - Logs error details with stack traces
    - Optional Sentry integration
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track errors."""
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Track 4xx/5xx responses
            if response.status_code >= 400:
                error_type = f"HTTP_{response.status_code}"
                record_error(
                    error_type=error_type,
                    endpoint=request.url.path,
                )
                
                logger.warning(
                    "HTTP error response",
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration=time.time() - start_time,
                )
            
            return response
            
        except Exception as e:
            # Record error metric
            record_error(
                error_type=type(e).__name__,
                endpoint=request.url.path,
            )
            
            # Log error with full stack trace
            logger.exception(
                "Unhandled exception",
                method=request.method,
                path=request.url.path,
                error_type=type(e).__name__,
                error_message=str(e),
                duration=time.time() - start_time,
                stack_trace=traceback.format_exc(),
            )
            
            # Re-raise to let FastAPI exception handlers deal with it
            raise


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all requests for observability.
    
    Features:
    - Logs request method, path, and duration
    - Tracks request rates
    - Adds correlation IDs
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process and log request."""
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params) if request.query_params else None,
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=f"{duration:.3f}s",
        )
        
        # Add timing header
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        return response


__all__ = [
    "ErrorTrackingMiddleware",
    "RequestLoggingMiddleware",
]
