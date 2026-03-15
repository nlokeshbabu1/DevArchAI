"""Pydantic schemas package."""

from app.schemas.auth import (
    APIKeyResponse,
    Token,
    TokenData,
    UserCreate,
    UserLogin,
    UserResponse,
    UserRole,
    UserUpdate,
)
from app.schemas.common import (
    BulkOperationResponse,
    ErrorResponse,
    HealthResponse,
    HealthStatus,
    MessageResponse,
    PaginatedResponse,
    PaginationParams,
)
from app.schemas.finding import (
    Category,
    FindingListResponse,
    FindingResponse,
    FindingUpdate,
    Severity,
)
from app.schemas.report import (
    CategoryScore,
    ReportDownloadResponse,
    ReportListResponse,
    ReportResponse,
    ReportSummary,
)
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryListResponse,
    RepositoryResponse,
    RepositoryUpdate,
)
from app.schemas.scan import (
    ScanCancelResponse,
    ScanCreate,
    ScanListResponse,
    ScanProgressResponse,
    ScanResponse,
    ScanStatus,
)

__all__ = [
    # Auth
    "Token",
    "TokenData",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserUpdate",
    "APIKeyResponse",
    "UserRole",
    # Repository
    "RepositoryCreate",
    "RepositoryUpdate",
    "RepositoryResponse",
    "RepositoryListResponse",
    # Scan
    "ScanCreate",
    "ScanResponse",
    "ScanListResponse",
    "ScanProgressResponse",
    "ScanCancelResponse",
    "ScanStatus",
    # Finding
    "FindingResponse",
    "FindingListResponse",
    "FindingUpdate",
    "Severity",
    "Category",
    # Report
    "ReportResponse",
    "ReportListResponse",
    "ReportDownloadResponse",
    "ReportSummary",
    "CategoryScore",
    # Common
    "HealthStatus",
    "HealthResponse",
    "PaginationParams",
    "PaginatedResponse",
    "MessageResponse",
    "ErrorResponse",
    "BulkOperationResponse",
]
