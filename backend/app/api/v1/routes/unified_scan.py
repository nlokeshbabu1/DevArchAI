"""
Unified Scan API - Works for BOTH guest and authenticated users.

Provides real-time progress tracking with step-by-step updates.
"""

import structlog
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_optional_user
from app.db.session import get_db, get_sync_session_factory
from app.models.anonymous_scan import AnonymousScan
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.services.scan_progress_store import get_scan_progress_store
from app.workers.tasks.scan_repository import SyncScanService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/scan", tags=["Unified Scan"])


class UnifiedScanRequest(BaseModel):
    """Request model for unified scan endpoint."""
    repository_url: str
    branch: str = "main"
    include_ai_explanations: bool = True


@router.post("/start", response_model=Dict[str, Any])
async def start_unified_scan(
    request: UnifiedScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Start a unified scan that works for BOTH guest and authenticated users.

    Returns:
    - scan_id: Unique identifier for tracking progress
    - session_token: For guest users to retrieve results
    - status: Initial scan status
    """
    try:
        # Generate identifiers
        scan_id = str(uuid4())
        session_token = None
        
        # For guest users, create anonymous scan record
        if not current_user:
            session_token = AnonymousScan.generate_session_token()
            expires_at = AnonymousScan.get_expiry()
            
            # Extract repo name
            repo_name = request.repository_url.rstrip("/").split("/")[-1].replace(".git", "")
            
            # Create anonymous scan session
            anon_scan = AnonymousScan(
                session_token=session_token,
                repository_url=request.repository_url,
                repository_name=repo_name,
                branch=request.branch,
                expires_at=expires_at,
                status="pending",
                linked_scan_id=scan_id,  # Link to scan_id from the start
            )
            db.add(anon_scan)
            logger.info(f"Anonymous scan session created: {session_token}")
        
        # Create scan record with the SAME ID used for progress tracking
        scan = Scan(
            id=uuid4(),  # This will be converted to string for scan_id
            user_id=current_user.id if current_user else None,
            repository_url=request.repository_url,
            branch=request.branch,
            status=ScanStatus.PENDING,
            progress=0,
        )
        
        # Use the scan's UUID as scan_id for progress tracking
        scan_id = str(scan.id)
        
        db.add(scan)
        await db.commit()
        await db.refresh(scan)
        
        # Initialize progress tracking with the SAME scan_id
        store = get_scan_progress_store()
        await store.create_scan(scan_id)
        await store.add_log(scan_id, f"Scan started for {request.repository_url}")
        await store.add_log(scan_id, f"Branch: {request.branch}")
        
        # Run scan synchronously with progress tracking
        try:
            SessionLocal = get_sync_session_factory()
            sync_db = SessionLocal()
            try:
                scan_service = SyncScanService(
                    db=sync_db,
                    include_ai_explanations=request.include_ai_explanations,
                    progress_store=store,
                    scan_id=scan_id,
                )
                
                # Get fresh scan from sync db using the SAME ID
                from app.models.scan import Scan as SyncScan
                sync_scan = sync_db.get(SyncScan, scan.id)
                
                if sync_scan:
                    # Execute scan synchronously with progress tracking
                    updated_scan = scan_service.execute_scan(sync_scan)
                    
                    # Copy results back to async session
                    scan.status = updated_scan.status
                    scan.progress = updated_scan.progress
                    scan.overall_score = updated_scan.overall_score
                    scan.security_score = updated_scan.security_score
                    scan.completed_at = updated_scan.completed_at
                    await db.commit()
                    
                    logger.info(f"Scan completed: {scan.status.value}, score: {scan.overall_score}")
                else:
                    logger.error(f"Scan not found in sync DB: {scan.id}")
                    raise Exception(f"Scan not found: {scan.id}")
            finally:
                sync_db.close()
                
        except Exception as scan_error:
            error_msg = str(scan_error)
            logger.exception(f"Scan failed: {error_msg}")
            
            # Update scan status to failed
            scan.status = ScanStatus.FAILED
            scan.error_message = error_msg
            await db.commit()
            
            # Update progress store
            await store.fail_scan(scan_id, error_msg)
            
            # For guest users, update anonymous scan status too
            if not current_user and session_token:
                result = await db.execute(
                    select(AnonymousScan).where(AnonymousScan.session_token == session_token)
                )
                anon_scan = result.scalar_one_or_none()
                if anon_scan:
                    anon_scan.status = "failed"
                    await db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Scan failed: {error_msg}",
            )
        
        # Return response
        return {
            "scan_id": scan_id,
            "session_token": session_token,
            "status": "running",
            "message": "Scan started successfully",
            "repository_url": request.repository_url,
            "branch": request.branch,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to start scan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start scan: {str(e)}",
        )


@router.get("/status/{scan_id}", response_model=Dict[str, Any])
async def get_scan_status(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get real-time scan progress status.
    
    Returns current step, progress percentage, and logs.
    Works for BOTH guest and authenticated users.
    """
    from app.services.scan_progress_store import get_scan_progress_store

    store = get_scan_progress_store()
    progress = await store.get_progress(scan_id)

    if not progress:
        # Return scan status from database if progress not found
        result = await db.execute(select(Scan).where(Scan.id == scan_id))
        scan = result.scalar_one_or_none()
        
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found",
            )
        
        # Check access for authenticated scans
        if scan.user_id and not current_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authentication required",
            )
        
        if scan.user_id and current_user and scan.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        
        # Return completed scan data
        return {
            "scan_id": str(scan.id),
            "status": scan.status.value,
            "progress": 100 if scan.status == 'completed' else scan.progress,
            "current_step": "Scan completed" if scan.status == 'completed' else scan.status.value,
            "steps": [],
            "detected_stack": [],
            "logs": [f"Scan {scan.status.value} at {scan.created_at}"],
            "created_at": scan.created_at.isoformat(),
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
            "error_message": scan.error_message,
        }

    return {
        "scan_id": progress.scan_id,
        "status": progress.status,
        "progress": progress.progress,
        "current_step": progress.current_step,
        "steps": [step.dict() for step in progress.steps],
        "detected_stack": progress.detected_stack,
        "logs": progress.logs,
        "created_at": progress.created_at.isoformat(),
        "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
        "error_message": progress.error_message,
    }


@router.get("/results/{scan_id}", response_model=Dict[str, Any])
async def get_scan_results(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get complete scan results after completion.
    
    Returns:
    - Security score
    - Findings with severity counts
    - AI suggestions
    - Detected technology stack
    """
    # Get scan
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Check access
    if scan.user_id and not current_user:
        raise HTTPException(status_code=403, detail="Authentication required")
    
    if scan.user_id and current_user and scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if scan.status != ScanStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Scan not completed. Status: {scan.status.value}",
        )
    
    # Get findings
    from app.models.finding import Finding
    findings_result = await db.execute(
        select(Finding).where(Finding.scan_id == scan_id)
    )
    findings = findings_result.scalars().all()
    
    # Count by severity
    severity_counts = {}
    for f in findings:
        severity = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    # Get AI suggestions
    from app.models.ai_suggestion import AISuggestion
    suggestions_result = await db.execute(
        select(AISuggestion).where(AISuggestion.scan_id == scan_id)
    )
    suggestions = suggestions_result.scalars().all()
    
    return {
        "scan_id": str(scan.id),
        "repository_url": scan.repository_url,
        "branch": scan.branch,
        "status": "completed",
        "overall_score": scan.overall_score,
        "security_score": scan.security_score,
        "scalability_score": scan.scalability_score,
        "reliability_score": scan.reliability_score,
        "cost_score": scan.cost_score,
        "observability_score": scan.observability_score,
        "findings_count": len(findings),
        "severity_counts": severity_counts,
        "findings": [
            {
                "id": str(f.id),
                "rule_name": f.rule_name,
                "severity": f.severity.value if hasattr(f.severity, 'value') else str(f.severity),
                "category": f.category.value if hasattr(f.category, 'value') else str(f.category),
                "description": f.description,
                "recommendation": f.recommendation,
                "file_path": f.file_path,
                "ai_explanation": f.ai_explanation,
            }
            for f in findings
        ],
        "ai_suggestions_count": len(suggestions),
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        "analysis_duration_seconds": scan.analysis_duration_seconds,
    }
