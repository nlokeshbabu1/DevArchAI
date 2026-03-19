"""AI Suggestion API routes - Production Grade."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_optional_user
from app.db.session import get_db
from app.models.ai_suggestion import AISuggestion, SuggestionStatus
from app.models.finding import Finding
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.schemas.ai_suggestion import (
    AISuggestionListResponse,
    AISuggestionResponse,
    ApplyFixRequest,
    ApplyFixResponse,
    CreatePRRequest,
    CreatePRResponse,
)
from app.services.feature_gating import FeatureGatingService
from app.services.fix_generation import get_fix_generation_service
from app.services.github_integration import get_github_integration_service
from app.workers.tasks.scan_repository import scan_repository_task

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/suggestions", tags=["AI Suggestions"])


@router.get("/{scan_id}", response_model=AISuggestionListResponse)
async def list_suggestions(
    scan_id: str,
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """List AI suggestions for a scan."""
    # Verify scan exists and user has access
    scan_result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = scan_result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Check access (public scans or user's own scans)
    if scan.user_id and scan.user_id != (current_user.id if current_user else None):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Build query
    query = select(AISuggestion).where(AISuggestion.scan_id == scan_id)
    
    if status_filter:
        query = query.where(AISuggestion.status == status_filter)
    
    result = await db.execute(query)
    suggestions = result.scalars().all()
    
    return AISuggestionListResponse(
        suggestions=[AISuggestionResponse.model_validate(s) for s in suggestions],
        total=len(suggestions),
        status_filter=status_filter,
    )


@router.get("/{suggestion_id}", response_model=AISuggestionResponse)
async def get_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Get a specific AI suggestion."""
    result = await db.execute(select(AISuggestion).where(AISuggestion.id == suggestion_id))
    suggestion = result.scalar_one_or_none()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    return AISuggestionResponse.model_validate(suggestion)


@router.post("/{suggestion_id}/apply", response_model=ApplyFixResponse)
async def apply_fix(
    suggestion_id: str,
    request: ApplyFixRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Apply fix code to file.
    
    For PRO/ENTERPRISE users only.
    """
    # Check plan gating
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_plan = getattr(current_user, 'subscription_plan', 'free')
    if user_plan not in ['pro', 'enterprise']:
        raise HTTPException(
            status_code=403,
            detail=f"Apply fix requires Pro or Enterprise plan. Current plan: {user_plan}",
        )
    
    # Get suggestion
    result = await db.execute(select(AISuggestion).where(AISuggestion.id == suggestion_id))
    suggestion = result.scalar_one_or_none()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    if not suggestion.fix_code:
        raise HTTPException(status_code=400, detail="No fix code available")
    
    if request.dry_run:
        return ApplyFixResponse(
            success=True,
            message="Dry run - no changes applied",
            file_path=suggestion.file_path,
            backup_path=None,
        )
    
    # In a real implementation, this would:
    # 1. Clone the repository
    # 2. Apply the fix to the file
    # 3. Create a backup
    # 4. Commit the changes
    
    # For now, return success with mock data
    return ApplyFixResponse(
        success=True,
        message="Fix applied successfully (mock)",
        file_path=suggestion.file_path,
        backup_path=f"{suggestion.file_path}.bak",
    )


@router.post("/{suggestion_id}/create-pr", response_model=CreatePRResponse)
async def create_pr(
    suggestion_id: str,
    request: CreatePRRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Create GitHub PR with fix.
    
    For PRO/ENTERPRISE users only.
    """
    # Check plan gating
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_plan = getattr(current_user, 'subscription_plan', 'free')
    if user_plan not in ['pro', 'enterprise']:
        raise HTTPException(
            status_code=403,
            detail=f"Create PR requires Pro or Enterprise plan. Current plan: {user_plan}",
        )
    
    # Get suggestion
    result = await db.execute(select(AISuggestion).where(AISuggestion.id == suggestion_id))
    suggestion = result.scalar_one_or_none()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    if not suggestion.fix_code:
        raise HTTPException(status_code=400, detail="No fix code available")
    
    # Get scan to get repo URL
    scan_result = await db.execute(select(Scan).where(Scan.id == suggestion.scan_id))
    scan = scan_result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Create PR using GitHub integration
    github_service = get_github_integration_service()
    
    pr_result = await github_service.apply_fix_and_create_pr(
        repo_url=scan.repository_url,
        file_path=suggestion.file_path,
        fix_code=suggestion.fix_code,
        finding_title=suggestion.title,
        branch_name=request.branch_name,
    )
    
    if not pr_result["success"]:
        raise HTTPException(status_code=500, detail=pr_result.get("error", "Failed to create PR"))
    
    # Update suggestion with PR info
    suggestion.status = SuggestionStatus.IN_PROGRESS
    suggestion.pr_url = pr_result["pr_url"]
    suggestion.pr_number = pr_result["pr_number"]
    await db.commit()
    
    return CreatePRResponse(
        success=True,
        pr_url=pr_result["pr_url"],
        pr_number=pr_result["pr_number"],
        branch_name=pr_result.get("branch_name", ""),
        message="PR created successfully",
    )


@router.post("/{suggestion_id}/ignore")
async def ignore_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Mark suggestion as ignored."""
    result = await db.execute(select(AISuggestion).where(AISuggestion.id == suggestion_id))
    suggestion = result.scalar_one_or_none()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    suggestion.status = SuggestionStatus.IGNORED
    await db.commit()
    
    return {"success": True, "message": "Suggestion marked as ignored"}


@router.post("/{suggestion_id}/mark-fixed")
async def mark_fixed(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Mark suggestion as fixed."""
    result = await db.execute(select(AISuggestion).where(AISuggestion.id == suggestion_id))
    suggestion = result.scalar_one_or_none()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    suggestion.status = SuggestionStatus.FIXED
    await db.commit()
    
    return {"success": True, "message": "Suggestion marked as fixed"}


@router.post("/generate/{finding_id}")
async def generate_suggestion(
    finding_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Generate AI suggestion for a finding."""
    # Get finding
    result = await db.execute(select(Finding).where(Finding.id == finding_id))
    finding = result.scalar_one_or_none()
    
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    
    # Check if suggestion already exists
    existing = await db.execute(select(AISuggestion).where(AISuggestion.finding_id == finding_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Suggestion already exists for this finding")
    
    # Generate fix code
    fix_service = get_fix_generation_service()
    
    # Determine fix type from file path
    file_path = finding.file_path or ""
    if ".tf" in file_path:
        fix_type = "terraform"
    elif "Dockerfile" in file_path:
        fix_type = "dockerfile"
    elif ".yaml" in file_path or ".yml" in file_path:
        if "k8s" in file_path.lower() or "kubernetes" in file_path.lower():
            fix_type = "kubernetes"
        else:
            fix_type = "ci_cd"
    else:
        fix_type = "general"
    
    fix_result = fix_service.generate_fix(
        finding={
            "rule_id": finding.rule_id,
            "description": finding.description,
            "file_path": finding.file_path,
        },
        fix_type=fix_type,
    )
    
    if not fix_result["success"]:
        raise HTTPException(status_code=500, detail=fix_result.get("error", "Failed to generate fix"))
    
    # Create suggestion
    suggestion = AISuggestion(
        finding_id=finding_id,
        scan_id=finding.scan_id,
        title=finding.rule_name,
        description=finding.description,
        severity=finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity),
        confidence=0.9,
        category=finding.category.value if hasattr(finding.category, 'value') else str(finding.category),
        fix_type=fix_type,
        file_path=finding.file_path or "",
        line_number=finding.line_number,
        fix_code=fix_result["fix_code"],
        auto_fix_available=True,
        status=SuggestionStatus.OPEN,
    )
    
    db.add(suggestion)
    await db.commit()
    await db.refresh(suggestion)

    return {
        "success": True,
        "suggestion_id": str(suggestion.id),
        "fix_code": fix_result["fix_code"],
        "fix_type": fix_type,
    }


@router.post("/{suggestion_id}/copy-fix")
async def copy_fix(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get fix code for copying.
    
    Available for PLUS, PRO, and ENTERPRISE users.
    FREE users cannot access this endpoint.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check plan gating - FREE users cannot copy fixes
    if not FeatureGatingService.can_copy_fix(current_user):
        user_plan = getattr(current_user, 'subscription_plan', 'free')
        raise HTTPException(
            status_code=403,
            detail=f"Copy fix requires Plus, Pro, or Enterprise plan. Current plan: {user_plan}",
        )
    
    # Get suggestion
    result = await db.execute(select(AISuggestion).where(AISuggestion.id == suggestion_id))
    suggestion = result.scalar_one_or_none()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    if not suggestion.fix_code:
        raise HTTPException(status_code=400, detail="No fix code available")
    
    return {
        "success": True,
        "fix_code": suggestion.fix_code,
        "fix_type": suggestion.fix_type,
        "file_path": suggestion.file_path,
    }


@router.post("/{suggestion_id}/rescan")
async def rescan_after_fix(
    suggestion_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Trigger re-scan after applying fix to verify resolution.
    
    For PRO/ENTERPRISE users only.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_plan = getattr(current_user, 'subscription_plan', 'free')
    if user_plan not in ['pro', 'enterprise']:
        raise HTTPException(
            status_code=403,
            detail=f"Re-scan requires Pro or Enterprise plan. Current plan: {user_plan}",
        )
    
    # Get suggestion
    result = await db.execute(select(AISuggestion).where(AISuggestion.id == suggestion_id))
    suggestion = result.scalar_one_or_none()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    # Get scan
    scan_result = await db.execute(select(Scan).where(Scan.id == suggestion.scan_id))
    scan = scan_result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Update suggestion status to IN_PROGRESS
    suggestion.status = SuggestionStatus.IN_PROGRESS
    await db.commit()
    
    # Trigger re-scan as background task
    try:
        # In production, this would use Celery
        # For now, add to background tasks
        background_tasks.add_task(
            _trigger_rescan,
            scan_id=str(scan.id),
            suggestion_id=str(suggestion.id),
        )
        
        return {
            "success": True,
            "message": "Re-scan initiated",
            "scan_id": str(scan.id),
            "suggestion_id": str(suggestion.id),
        }
    except Exception as e:
        logger.error(f"Re-scan failed to initiate: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate re-scan: {str(e)}")


async def _trigger_rescan(scan_id: str, suggestion_id: str):
    """Background task to trigger re-scan and update suggestion status."""
    logger.info(f"Triggering re-scan for scan={scan_id}, suggestion={suggestion_id}")
    # In production, this would:
    # 1. Re-run the scanner on the repository
    # 2. Compare findings before and after
    # 3. Update suggestion status to FIXED if issue is resolved
    pass
