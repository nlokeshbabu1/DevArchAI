"""
Scan progress tracking schemas.
"""

from datetime import datetime
from enum import Enum

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
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class ScanProgressResponse(BaseModel):
    """Real-time scan progress response."""
    scan_id: str
    status: str  # pending, running, completed, failed
    progress: int = Field(ge=0, le=100, description="Overall progress percentage")
    current_step: str | None = None
    steps: list[ScanStep] = []
    detected_stack: list[str] = []
    logs: list[str] = []
    created_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None
    # Enhanced fields for better UI feedback
    stage: str | None = None  # cloned, detecting, scanning, ai, completed
    files_scanned: int = 0
    total_files: int = 0
    files_list: list[str] = []  # Actual file paths being scanned

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
