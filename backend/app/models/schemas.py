"""
Pydantic Schemas for API Request/Response
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class Severity(str, Enum):
    """Finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(str, Enum):
    """Analysis categories."""
    SECURITY = "security"
    SCALABILITY = "scalability"
    RELIABILITY = "reliability"
    COST = "cost"
    OBSERVABILITY = "observability"


class RuleFinding(BaseModel):
    """Individual rule finding."""
    
    rule_id: str = Field(..., description="Unique rule identifier")
    rule_name: str = Field(..., description="Human-readable rule name")
    severity: Severity = Field(..., description="Finding severity")
    category: Category = Field(..., description="Finding category")
    description: str = Field(..., description="What was found")
    recommendation: str = Field(..., description="How to fix")
    file_path: Optional[str] = Field(None, description="File where issue was found")
    line_number: Optional[int] = Field(None, description="Line number of issue")
    ai_explanation: Optional[str] = Field(None, description="AI-generated explanation")
    impact_analysis: Optional[str] = Field(None, description="AI impact analysis")
    confidence_score: float = Field(default=1.0, ge=0, le=1, description="Confidence in finding")


class CategoryScore(BaseModel):
    """Score for a specific category."""
    
    category: Category
    score: float = Field(ge=0, le=100)
    findings_count: int
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0


class AnalysisReport(BaseModel):
    """Complete analysis report."""
    
    # Metadata
    id: str = Field(..., description="Unique report ID")
    repository_url: str = Field(..., description="Analyzed repository URL")
    repository_name: str = Field(..., description="Repository name")
    commit_hash: Optional[str] = Field(None, description="Analyzed commit")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    analysis_duration_seconds: float = Field(..., description="Time taken for analysis")
    
    # Scores
    overall_score: float = Field(ge=0, le=100, description="Overall production readiness score")
    category_scores: List[CategoryScore] = Field(..., description="Scores per category")
    
    # Findings
    findings: List[RuleFinding] = Field(..., description="All findings")
    summary: Dict[str, int] = Field(..., description="Summary counts by severity")
    
    # AI Analysis
    executive_summary: Optional[str] = Field(None, description="AI-generated executive summary")
    risk_analysis: Optional[str] = Field(None, description="AI risk analysis")
    prioritized_recommendations: Optional[List[str]] = Field(None, description="Top recommendations")
    
    # Files Analyzed
    files_analyzed: List[str] = Field(default_factory=list, description="List of analyzed files")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "rpt_123456",
                "repository_url": "https://github.com/example/repo",
                "repository_name": "example/repo",
                "overall_score": 72.5,
                "category_scores": [
                    {"category": "security", "score": 65.0, "findings_count": 5},
                    {"category": "scalability", "score": 80.0, "findings_count": 2},
                ],
                "findings": [
                    {
                        "rule_id": "SEC-001",
                        "rule_name": "Missing State Locking",
                        "severity": "critical",
                        "category": "security",
                        "description": "Terraform state backend does not have locking enabled",
                        "recommendation": "Enable state locking using DynamoDB or similar",
                        "file_path": "terraform/backend.tf",
                    }
                ],
                "summary": {"critical": 1, "high": 2, "medium": 3, "low": 4, "info": 2},
            }
        }


class AnalysisRequest(BaseModel):
    """Request to analyze a repository."""
    
    repository_url: str = Field(..., description="GitHub repository URL")
    branch: Optional[str] = Field(default="main", description="Branch to analyze")
    commit_hash: Optional[str] = Field(None, description="Specific commit to analyze")
    include_ai_explanations: bool = Field(default=True, description="Include AI explanations")
    
    class Config:
        json_schema_extra = {
            "example": {
                "repository_url": "https://github.com/example/infrastructure",
                "branch": "main",
                "include_ai_explanations": True,
            }
        }


class AnalysisStatus(str, Enum):
    """Analysis job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisJob(BaseModel):
    """Analysis job status."""
    
    id: str
    repository_url: str
    status: AnalysisStatus
    progress: int = Field(ge=0, le=100, description="Progress percentage")
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    report_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]
