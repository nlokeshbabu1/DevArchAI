"""
Scan progress tracking schemas.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    """Status of a scan step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanStep(BaseModel):
    """Individual scan step."""
    name: str
    status: StepStatus
    progress: int = 0  # 0-100
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class ScanProgressResponse(BaseModel):
    """Real-time scan progress response."""
    scan_id: str
    status: str  # pending, running, completed, failed
    progress: int = Field(ge=0, le=100, description="Overall progress percentage")
    current_step: Optional[str] = None
    steps: List[ScanStep] = []
    detected_stack: List[str] = []
    logs: List[str] = []
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "scan_id": "scan-123456",
                "status": "running",
                "progress": 60,
                "current_step": "Running Terraform checks",
                "steps": [
                    {"name": "Connecting to GitHub", "status": "completed", "progress": 100},
                    {"name": "Fetching repository", "status": "completed", "progress": 100},
                    {"name": "Detecting technologies", "status": "completed", "progress": 100},
                    {"name": "Running security rules", "status": "running", "progress": 50},
                    {"name": "Generating AI suggestions", "status": "pending", "progress": 0},
                    {"name": "Calculating score", "status": "pending", "progress": 0}
                ],
                "detected_stack": ["terraform", "docker", "kubernetes"],
                "logs": [
                    "Cloning repository...",
                    "Terraform files detected",
                    "Running security rules..."
                ],
                "created_at": "2024-01-01T00:00:00Z"
            }
        }
