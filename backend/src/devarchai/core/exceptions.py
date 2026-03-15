"""Custom exceptions for the application."""

from typing import Any


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str = "An error occurred",
        status_code: int = 500,
        detail: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        self.headers = headers
        super().__init__(self.message)


class AuthenticationException(AppException):
    """Authentication failed."""

    def __init__(
        self,
        message: str = "Authentication failed",
        detail: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationException(AppException):
    """Authorization failed."""

    def __init__(
        self,
        message: str = "Access denied",
        detail: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=403,
            detail=detail,
        )


class NotFoundException(AppException):
    """Resource not found."""

    def __init__(
        self,
        resource_type: str = "Resource",
        resource_id: Any | None = None,
        message: str | None = None,
    ):
        if message is None:
            message = f"{resource_type} not found"
            if resource_id:
                message = f"{resource_type} with ID {resource_id} not found"

        super().__init__(
            message=message,
            status_code=404,
            detail=message,
        )


class ValidationException(AppException):
    """Validation failed."""

    def __init__(
        self,
        message: str = "Validation failed",
        detail: Any = None,
    ):
        super().__init__(
            message=message,
            status_code=400,
            detail=detail,
        )


class ScanNotFoundException(NotFoundException):
    """Scan not found."""

    def __init__(self, scan_id: Any):
        super().__init__(
            resource_type="Scan",
            resource_id=scan_id,
        )


class OrganizationNotFoundException(NotFoundException):
    """Organization not found."""

    def __init__(self, org_id: Any):
        super().__init__(
            resource_type="Organization",
            resource_id=org_id,
        )


class RepositoryNotFoundException(NotFoundException):
    """Repository not found."""

    def __init__(self, repo_id: Any):
        super().__init__(
            resource_type="Repository",
            resource_id=repo_id,
        )


class ProjectNotFoundException(NotFoundException):
    """Project not found."""

    def __init__(self, project_id: Any):
        super().__init__(
            resource_type="Project",
            resource_id=project_id,
        )


class ReportNotFoundException(NotFoundException):
    """Report not found."""

    def __init__(self, report_id: Any):
        super().__init__(
            resource_type="Report",
            resource_id=report_id,
        )


class FindingNotFoundException(NotFoundException):
    """Finding not found."""

    def __init__(self, finding_id: Any):
        super().__init__(
            resource_type="Finding",
            resource_id=finding_id,
        )


class SubscriptionNotFoundException(NotFoundException):
    """Subscription not found."""

    def __init__(self, org_id: Any):
        super().__init__(
            resource_type="Subscription",
            resource_id=org_id,
        )


class QuotaExceededException(AppException):
    """Quota exceeded."""

    def __init__(
        self,
        quota_type: str = "quota",
        limit: int | None = None,
    ):
        message = f"Quota exceeded for {quota_type}"
        if limit:
            message += f" (limit: {limit})"

        super().__init__(
            message=message,
            status_code=429,
            detail=message,
        )


class RateLimitExceededException(AppException):
    """Rate limit exceeded."""

    def __init__(
        self,
        limit: int,
        window: int,
    ):
        super().__init__(
            message=f"Rate limit exceeded. Limit: {limit} requests per {window} seconds",
            status_code=429,
            detail="Too many requests",
        )


class ConflictException(AppException):
    """Resource conflict."""

    def __init__(
        self,
        message: str = "Resource conflict",
        detail: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=409,
            detail=detail,
        )


class InternalServerException(AppException):
    """Internal server error."""

    def __init__(
        self,
        message: str = "Internal server error",
        detail: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=500,
            detail=detail,
        )


def setup_exception_handlers(app) -> None:
    """Setup global exception handlers for FastAPI app."""
    from fastapi import FastAPI, Request, status
    from fastapi.responses import JSONResponse
    
    if not isinstance(app, FastAPI):
        return
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """Handle application exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail or exc.message},
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unhandled exceptions."""
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred"},
        )
