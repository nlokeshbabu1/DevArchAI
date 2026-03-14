"""
Anonymous scan endpoints.

Allows unauthenticated users to:
- Submit repository URLs for scanning
- View limited scan results (score, issue counts, titles)
- See blurred AI suggestions with login CTA
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.anonymous_scan import AnonymousScan
from app.models.finding import Finding
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.schemas.common import MessageResponse

from pydantic import BaseModel

router = APIRouter(prefix="/public", tags=["Public Scans"])


class PublicScanRequest(BaseModel):
    """Request model for public scan endpoint."""
    repository_url: str
    branch: str = "main"


@router.post("/scan", response_model=dict)
async def create_anonymous_scan(
    request: PublicScanRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create an anonymous scan session.
    
    No authentication required.
    Returns a session token to retrieve results.
    """
    try:
        # Generate session token
        session_token = AnonymousScan.generate_session_token()
        expires_at = AnonymousScan.get_expiry()
        
        # Extract repo name from URL
        repo_name = request.repository_url.rstrip("/").split("/")[-1].replace(".git", "")
        
        # Create anonymous scan record
        anon_scan = AnonymousScan(
            session_token=session_token,
            repository_url=request.repository_url,
            repository_name=repo_name,
            branch=request.branch,
            expires_at=expires_at,
            status="pending",
        )
        
        db.add(anon_scan)
        await db.commit()
        await db.refresh(anon_scan)
        
        # TODO: Trigger actual scan job here
        # For now, we'll create a regular scan with anonymous user
        # In production, this would queue a Celery task
        
        return {
            "session_token": session_token,
            "repository_name": repo_name,
            "status": "pending",
            "message": "Scan started. Use the session_token to retrieve results.",
            "expires_at": expires_at.isoformat(),
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create scan session: {str(e)}",
        )


@router.get("/scan/{session_token}")
async def get_anonymous_scan_results(
    session_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get anonymous scan results.
    
    Returns:
    - Security score
    - Issue severity counts
    - Issue titles and descriptions
    - BLURRED AI suggestions
    
    No authentication required.
    """
    # Find scan session
    result = await db.execute(
        select(AnonymousScan).where(
            AnonymousScan.session_token == session_token,
            AnonymousScan.expires_at > datetime.utcnow(),
        )
    )
    anon_scan = result.scalar_one_or_none()
    
    if not anon_scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan session not found or expired",
        )
    
    # If scan is still pending, return status
    if anon_scan.status == "pending":
        return {
            "session_token": session_token,
            "status": "pending",
            "message": "Scan is in progress. Please check back in a few moments.",
            "repository_name": anon_scan.repository_name,
        }
    
    # Return public results
    return {
        "session_token": session_token,
        "status": anon_scan.status,
        "repository_name": anon_scan.repository_name,
        "repository_url": anon_scan.repository_url,
        "security_score": anon_scan.security_score,
        "severity_counts": {
            "critical": anon_scan.critical_count,
            "high": anon_scan.high_count,
            "medium": anon_scan.medium_count,
            "low": anon_scan.low_count,
        },
        "findings": json.loads(anon_scan.findings_summary) if anon_scan.findings_summary else [],
        "ai_suggestions_blurred": True,  # Always blurred for anonymous users
        "ai_suggestions": None,  # Hidden until login
        "login_required": True,
        "message": "Login to unlock AI-powered remediation suggestions",
    }


@router.post("/scan/{session_token}/claim")
async def claim_anonymous_scan(
    session_token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Claim an anonymous scan and associate it with a user account.
    
    Called after user logs in or signs up.
    Converts anonymous scan to authenticated scan.
    """
    from app.core.security import get_current_user
    
    # Find anonymous scan
    result = await db.execute(
        select(AnonymousScan).where(
            AnonymousScan.session_token == session_token,
            AnonymousScan.expires_at > datetime.utcnow(),
        )
    )
    anon_scan = result.scalar_one_or_none()
    
    if not anon_scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan session not found or expired",
        )
    
    # Create authenticated scan
    auth_scan = Scan(
        user_id=current_user.id,
        repository_url=anon_scan.repository_url,
        branch=anon_scan.branch,
        status=ScanStatus.COMPLETED if anon_scan.status == "completed" else ScanStatus.PENDING,
        security_score=float(anon_scan.security_score.split("/")[0]) if anon_scan.security_score else None,
    )
    
    db.add(auth_scan)
    
    # Mark anonymous scan as claimed
    anon_scan.status = "claimed"
    
    await db.commit()
    await db.refresh(auth_scan)
    
    return {
        "scan_id": str(auth_scan.id),
        "message": "Scan claimed successfully. Full results now available.",
    }


@router.delete("/scan/{session_token}")
async def delete_anonymous_scan(
    session_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete an anonymous scan session."""
    result = await db.execute(
        select(AnonymousScan).where(AnonymousScan.session_token == session_token)
    )
    anon_scan = result.scalar_one_or_none()
    
    if not anon_scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan session not found",
        )
    
    await db.delete(anon_scan)
    await db.commit()

    return MessageResponse(message="Scan session deleted")
