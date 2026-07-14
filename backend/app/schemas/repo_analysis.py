"""Repository Analysis schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class RepoAnalysisRequest(BaseModel):
    """Request to analyze a GitHub repository."""

    repo_url: str = Field(..., description="GitHub repository URL")
    branch: str | None = Field(default="main", description="Branch to analyze")

    class Config:
        json_schema_extra = {
            "example": {
                "repo_url": "https://github.com/example/infrastructure",
                "branch": "main"
            }
        }


class DevOpsStack(BaseModel):
    """Detected DevOps stack."""

    # Containers
    docker: bool = False
    docker_files: list[str] = Field(default_factory=list)

    # Infrastructure as Code
    terraform: bool = False
    terraform_files: list[str] = Field(default_factory=list)
    pulumi: bool = False
    pulumi_files: list[str] = Field(default_factory=list)
    cloudformation: bool = False
    cloudformation_files: list[str] = Field(default_factory=list)
    ansible: bool = False
    ansible_files: list[str] = Field(default_factory=list)

    # Kubernetes
    kubernetes: bool = False
    kubernetes_files: list[str] = Field(default_factory=list)
    helm: bool = False
    helm_files: list[str] = Field(default_factory=list)
    kustomize: bool = False
    kustomize_files: list[str] = Field(default_factory=list)

    # CI/CD
    cicd: str | None = None
    cicd_files: list[str] = Field(default_factory=list)

    # Monitoring
    monitoring: bool = False
    monitoring_files: list[str] = Field(default_factory=list)
    prometheus: bool = False
    prometheus_files: list[str] = Field(default_factory=list)
    grafana: bool = False
    grafana_files: list[str] = Field(default_factory=list)
    datadog: bool = False
    datadog_files: list[str] = Field(default_factory=list)

    # Service Mesh
    service_mesh: bool = False
    service_mesh_files: list[str] = Field(default_factory=list)
    istio: bool = False
    istio_files: list[str] = Field(default_factory=list)

    # Security
    security_scanning: bool = False
    security_files: list[str] = Field(default_factory=list)


class RepoAnalysisResponse(BaseModel):
    """Response from repository analysis."""

    # Repository info
    repo: str = Field(..., description="Repository full name (owner/repo)")
    repo_url: str
    repo_owner: str
    repo_name: str

    # DevOps stack
    devops_stack: DevOpsStack

    # Scores
    devops_score: float | None = Field(None, description="Overall DevOps score (0-100)")

    # Analysis metadata
    files_analyzed: int = 0
    analysis_id: int | None = None

    # Timestamps
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class RepoAnalysisListItem(BaseModel):
    """Summary item for analysis list."""

    id: int
    repo_url: str
    repo_full_name: str
    devops_score: float | None
    has_docker: bool
    has_terraform: bool
    has_kubernetes: bool
    has_cicd: bool
    cicd_type: str | None
    created_at: datetime


class RepoAnalysisListResponse(BaseModel):
    """List of repository analyses."""

    analyses: list[RepoAnalysisListItem]
    total: int
    page: int
    page_size: int


class MissingBestPractice(BaseModel):
    """Missing best practice recommendation."""

    category: str
    title: str
    description: str
    severity: str  # critical, high, medium, low
    recommendation: str


class BestPracticesResponse(BaseModel):
    """Missing best practices analysis."""

    repo: str
    missing_practices: list[MissingBestPractice]
    total_missing: int
    score: float
