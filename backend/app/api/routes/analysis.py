"""
API Routes for Analysis
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
import uuid
from datetime import datetime

from app.models.schemas import AnalysisRequest, AnalysisReport, AnalysisJob, AnalysisStatus
from app.services.analysis import AnalysisService
from app.services.github import GitHubService
from app.core.exceptions import AnalysisException, RepositoryNotFoundException

router = APIRouter()

# In-memory job store (use Redis in production)
active_jobs: dict[str, AnalysisJob] = {}


@router.post("/analyze", response_model=AnalysisJob, status_code=202)
async def start_analysis(request: AnalysisRequest):
    """
    Start analysis of a GitHub repository.
    
    Returns a job ID that can be used to check status and retrieve results.
    """
    job_id = str(uuid.uuid4())
    
    # Create job record
    job = AnalysisJob(
        id=job_id,
        repository_url=request.repository_url,
        status=AnalysisStatus.PENDING,
        progress=0,
        created_at=datetime.utcnow(),
    )
    active_jobs[job_id] = job
    
    # Start analysis in background
    async def run_analysis():
        try:
            job.status = AnalysisStatus.PROCESSING
            job.progress = 10
            
            # Clone repository
            github_service = GitHubService()
            repo_path = await github_service.clone_repository(
                request.repository_url,
                request.branch,
                request.commit_hash,
            )
            
            job.progress = 30
            
            # Run analysis
            analysis_service = AnalysisService()
            report = await analysis_service.analyze_repository(
                repo_path=repo_path,
                include_ai_explanations=request.include_ai_explanations,
                progress_callback=lambda p: setattr(job, 'progress', p),
            )
            
            job.status = AnalysisStatus.COMPLETED
            job.progress = 100
            job.completed_at = datetime.utcnow()
            job.report_id = report.id
            
        except Exception as e:
            job.status = AnalysisStatus.FAILED
            job.error_message = str(e)
            raise
    
    # Start background task
    BackgroundTasks().add_task(run_analysis)
    
    return job


@router.get("/analysis/{job_id}", response_model=AnalysisJob)
async def get_analysis_status(job_id: str):
    """Get the status of an analysis job."""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return active_jobs[job_id]


@router.get("/reports/{report_id}", response_model=AnalysisReport)
async def get_report(report_id: str):
    """Get analysis report by ID."""
    # In production, fetch from database/S3
    raise HTTPException(status_code=501, detail="Not implemented - use download endpoint")


@router.get("/reports/{report_id}/download")
async def download_report(report_id: str):
    """Download analysis report as JSON."""
    # In production, fetch from S3
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/analysis/{job_id}/report", response_model=AnalysisReport)
async def get_report_by_job(job_id: str):
    """Get report for completed analysis job."""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = active_jobs[job_id]
    
    if job.status != AnalysisStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed. Status: {job.status}",
        )
    
    if not job.report_id:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # In production, fetch from database
    raise HTTPException(status_code=501, detail="Not implemented - report storage pending")
