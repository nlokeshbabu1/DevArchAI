"""Core exceptions and error handlers."""

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger

logger = get_logger(__name__)


def _serialize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert pydantic validation errors into JSON-serializable dictionaries.

    ``ctx`` may contain non-serializable exception objects (e.g. the original
    ValueError raised by a field_validator), which would otherwise break the
    response handler and surface as an unhandled 500. The raw ``input`` value
    is deliberately dropped to avoid echoing attacker-controlled payloads in
    error responses (reflection/XSS vector and a known ZAP SQLi false positive).
    """
    serialized: list[dict[str, Any]] = []
    for err in errors:
        clean = {key: _sanitize_error_value(value) for key, value in err.items() if key != "input"}
        serialized.append(clean)
    return serialized


def _sanitize_error_value(value: Any) -> Any:
    """Recursively replace non-JSON-serializable values with strings."""
    if isinstance(value, Exception):
        return f"{type(value).__name__}: {value}"
    if isinstance(value, dict):
        return {str(k): _sanitize_error_value(v) for k, v in value.items()}
    if isinstance(value, tuple | list):
        return [_sanitize_error_value(item) for item in value]
    return value


class DevArchAIException(Exception):
    """Base exception for DevArchAI."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


# Application-specific exceptions
class AnalysisException(DevArchAIException):
    """Exception raised during analysis."""

    def __init__(self, message: str, error_code: str = "ANALYSIS_ERROR"):
        super().__init__(message, status_code=400, error_code=error_code)


class RepositoryNotFoundException(DevArchAIException):
    """Exception raised when repository is not found."""

    def __init__(self, repo_url: str):
        super().__init__(
            f"Repository not found: {repo_url}",
            status_code=404,
            error_code="REPOSITORY_NOT_FOUND",
        )


class InvalidRepositoryException(DevArchAIException):
    """Exception raised for invalid repository."""

    def __init__(self, message: str):
        super().__init__(message, status_code=400, error_code="INVALID_REPOSITORY")


class ParsingException(DevArchAIException):
    """Exception raised during file parsing."""

    def __init__(self, file_path: str, message: str):
        super().__init__(
            f"Failed to parse {file_path}: {message}",
            status_code=400,
            error_code="PARSING_ERROR",
        )


class RateLimitExceededException(DevArchAIException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self):
        super().__init__(
            "Rate limit exceeded. Please try again later.",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
        )


class AIServiceException(DevArchAIException):
    """Exception raised when AI service fails."""

    def __init__(self, message: str):
        super().__init__(message, status_code=503, error_code="AI_SERVICE_UNAVAILABLE")


class AuthenticationException(DevArchAIException):
    """Exception raised for authentication failures."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            detail,
            status_code=401,
            error_code="AUTHENTICATION_FAILED",
        )


class AuthorizationException(DevArchAIException):
    """Exception raised for authorization failures."""

    def __init__(self, detail: str = "Access denied"):
        super().__init__(
            detail,
            status_code=403,
            error_code="AUTHORIZATION_FAILED",
        )


class ScanNotFoundException(DevArchAIException):
    """Exception raised when scan is not found."""

    def __init__(self, scan_id: int):
        super().__init__(
            f"Scan not found: {scan_id}",
            status_code=404,
            error_code="SCAN_NOT_FOUND",
        )


class ScanTimeoutError(DevArchAIException):
    """Exception raised when scan exceeds time limit."""

    def __init__(self, message: str = "Scan timed out"):
        super().__init__(
            message,
            status_code=408,
            error_code="SCAN_TIMEOUT",
        )


class ReportNotFoundException(DevArchAIException):
    """Exception raised when report is not found."""

    def __init__(self, report_id: int):
        super().__init__(
            f"Report not found: {report_id}",
            status_code=404,
            error_code="REPORT_NOT_FOUND",
        )


class DatabaseException(DevArchAIException):
    """Exception raised for database errors."""

    def __init__(self, message: str):
        super().__init__(message, status_code=500, error_code="DATABASE_ERROR")


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup global exception handlers."""

    @app.exception_handler(DevArchAIException)
    async def devarchai_exception_handler(request: Request, exc: DevArchAIException) -> JSONResponse:
        """Handle DevArchAI exceptions."""
        logger.error(
            "DevArchAI exception",
            error_code=exc.error_code,
            message=exc.message,
            path=request.url.path,
            method=request.method,
            **exc.details,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details if exc.details else None,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors."""
        errors = _serialize_validation_errors(exc.errors())
        logger.warning(
            "Validation error",
            errors=errors,
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": errors,
                }
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Handle database errors."""
        logger.exception(
            "Database error",
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "A database error occurred",
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions."""
        logger.warning(
            "HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail,
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unhandled exceptions."""
        logger.exception(
            "Unhandled exception",
            path=request.url.path,
            method=request.method,
            exception_type=type(exc).__name__,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                }
            },
        )
