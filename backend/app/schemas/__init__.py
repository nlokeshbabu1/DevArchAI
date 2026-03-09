"""Pydantic schemas package."""

from app.schemas.auth import (
    Token,
    TokenData,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    APIKeyResponse,
    UserRole,
)
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryUpdate,
    RepositoryResponse,
    RepositoryListResponse,
)
from app.schemas.scan import (
    ScanCreate,
    ScanResponse,
    ScanListResponse,
    ScanProgressResponse,
    ScanCancelResponse,
    ScanStatus,
)
from app.schemas.finding import (
    FindingResponse,
    FindingListResponse,
    FindingUpdate,
    Severity,
    Category,
)
from app.schemas.report import (
    ReportResponse,
    ReportListResponse,
    ReportDownloadResponse,
    ReportSummary,
    CategoryScore,
)
from app.schemas.common import (
    HealthStatus,
    HealthResponse,
    PaginationParams,
    PaginatedResponse,
    MessageResponse,
    ErrorResponse,
    BulkOperationResponse,
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
