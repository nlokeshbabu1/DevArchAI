"""GitHub App installation schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class InstallationCreate(BaseModel):
    """Schema for registering a GitHub App installation."""

    repository_url: str = Field(
        ...,
        description="Full GitHub repository URL (e.g., https://github.com/owner/repo)",
        example="https://github.com/example/my-repo",
    )
    installation_id: int = Field(
        ...,
        description="GitHub App installation ID",
        example=12345678,
    )


class InstallationResponse(BaseModel):
    """Schema for GitHub App installation response."""

    id: str
    repo_full_name: str
    installation_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class InstallationListResponse(BaseModel):
    """Schema for listing GitHub App installations."""

    installations: list[InstallationResponse]
    total: int


class InstallationValidateRequest(BaseModel):
    """Schema for validating a GitHub App installation."""

    repository_url: str = Field(
        ...,
        description="Full GitHub repository URL",
        example="https://github.com/example/my-repo",
    )
    installation_id: int = Field(
        ...,
        description="GitHub App installation ID to validate",
        example=12345678,
    )


class InstallationValidateResponse(BaseModel):
    """Schema for installation validation response."""

    installation_id: int
    app_id: int
    permissions: dict
    events: list[str]
    repository_selection: str | None
    repo_full_name: str
