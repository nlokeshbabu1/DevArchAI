"""Repository Analysis model for storing analysis results."""

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func

from app.db.base import Base


class RepoAnalysis(Base):
    """RepoAnalysis model for storing GitHub repository analysis results."""

    __tablename__ = "repo_analysis"

    id = Column(Integer, primary_key=True, index=True)

    # Tenant isolation
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Repository info
    repo_url = Column(String(500), nullable=False, index=True)
    repo_owner = Column(String(100), nullable=False)
    repo_name = Column(String(100), nullable=False)
    repo_full_name = Column(String(255), nullable=False)  # owner/repo

    # DevOps stack detection
    detected_stack = Column(JSON, nullable=True)  # Full stack detection result

    # Stack flags for quick queries
    has_docker = Column(Boolean, default=False, nullable=False)
    has_terraform = Column(Boolean, default=False, nullable=False)
    has_kubernetes = Column(Boolean, default=False, nullable=False)
    has_cicd = Column(Boolean, default=False, nullable=False)
    has_monitoring = Column(Boolean, default=False, nullable=False)
    has_helm = Column(Boolean, default=False, nullable=False)
    has_ansible = Column(Boolean, default=False, nullable=False)

    # CI/CD type
    cicd_type = Column(String(50), nullable=True)  # github_actions, gitlab_ci, jenkins, etc.

    # DevOps score (0-100)
    devops_score = Column(Float, nullable=True)

    # Analysis metadata
    files_analyzed = Column(Integer, default=0, nullable=False)
    analysis_version = Column(String(20), default="1.0", nullable=False)

    # Status
    status = Column(String(20), default="completed", nullable=False)  # pending, completed, failed
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<RepoAnalysis(id={self.id}, repo={self.repo_full_name})>"
