"""AI Suggestion API routes - Production Grade."""

import hashlib
from datetime import datetime

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.scan_access import assert_scan_read_access
from app.core.security import get_optional_user
from app.core.validators import parse_uuid
from app.db.session import get_db
from app.models.ai_suggestion import AISuggestion, SuggestionStatus
from app.models.finding import Finding
from app.models.scan import Scan
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
from app.services.entitlements import resolve_user_entitlements
from app.services.github_integration import get_github_integration_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/suggestions", tags=["AI Suggestions"])


def suggestion_to_response(s: AISuggestion) -> AISuggestionResponse:
    """Convert an AISuggestion record to the response format."""
    return AISuggestionResponse(
        id=str(s.id),
        finding_id=str(s.finding_id),
        scan_id=str(s.scan_id),
        title=s.title or "",
        description=s.description or "",
        severity=s.severity.value if hasattr(s.severity, 'value') else str(s.severity),
        confidence=s.confidence or 0.9,
        category=s.category.value if hasattr(s.category, 'value') else str(s.category),
        fix_type=s.fix_type.value if hasattr(s.fix_type, 'value') else str(s.fix_type),
        file_path=s.file_path or "",
        line_number=s.line_number,
        fix_code=s.fix_code,
        auto_fix_available=s.auto_fix_available or False,
        metadata=s.metadata if isinstance(s.metadata, dict) else None,
        status=s.status.value if hasattr(s.status, 'value') else str(s.status),
        applied_at=s.applied_at,
        pr_url=s.pr_url,
        pr_number=s.pr_number,
        created_at=s.created_at or datetime.utcnow(),
        updated_at=s.updated_at or datetime.utcnow(),
    )


async def _verify_suggestion_ownership(
    suggestion_id: str,
    current_user: User,
    db: AsyncSession,
) -> AISuggestion:
    """Verify the current user owns the scan associated with this suggestion."""
    parse_uuid(suggestion_id, "suggestion_id")
    result = await db.execute(select(AISuggestion).where(AISuggestion.id == suggestion_id))
    suggestion = result.scalar_one_or_none()

    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    scan_result = await db.execute(select(Scan).where(Scan.id == suggestion.scan_id))
    scan = scan_result.scalar_one_or_none()

    if not scan or scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return suggestion


@router.get("", response_model=AISuggestionListResponse)
async def list_all_suggestions(
    status_filter: str | None = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """List ALL AI suggestions from all user's scans.

    Returns both AISuggestion records AND AI-enriched findings.
    """
    if not current_user:
        # For anonymous users, return empty
        return AISuggestionListResponse(suggestions=[], total=0, status_filter=status_filter)

    # Get all user's scans
    scan_result = await db.execute(select(Scan.id).where(Scan.user_id == current_user.id))
    scan_ids = [str(row[0]) for row in scan_result.all()]

    if not scan_ids:
        return AISuggestionListResponse(suggestions=[], total=0, status_filter=status_filter)

    # Get AISuggestion records
    query = select(AISuggestion).where(AISuggestion.scan_id.in_(scan_ids))
    if status_filter:
        query = query.where(AISuggestion.status == status_filter)
    result = await db.execute(query)
    suggestions = result.scalars().all()

    # Also get AI-enriched findings (findings with ai_generated=true or ai_explanation)
    findings_query = (
        select(Finding)
        .where(Finding.scan_id.in_(scan_ids))
        .where(
            (Finding.ai_generated == True) |
            (Finding.ai_explanation.isnot(None)) |
            (Finding.summary.isnot(None))
        )
    )
    findings_result = await db.execute(findings_query)
    ai_findings = findings_result.scalars().all()

    # Convert findings to suggestion-like format if they're not already in suggestions
    existing_finding_ids = {s.finding_id for s in suggestions if s.finding_id}
    finding_suggestions = []
    for finding in ai_findings:
        if str(finding.id) not in existing_finding_ids:
            # Create a suggestion-like response from the finding
            finding_suggestions.append(AISuggestionResponse(
                id=str(finding.id),
                finding_id=str(finding.id),  # Use finding ID as finding_id
                scan_id=str(finding.scan_id),  # Include scan_id from finding
                title=finding.rule_name or f"Finding: {finding.rule_id}",
                description=finding.description or "",
                severity=finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity),
                confidence=finding.confidence or 0.8,
                category=finding.category.value if hasattr(finding.category, 'value') else str(finding.category),
                fix_type="ai_enriched",
                file_path=finding.file_path or "",
                line_number=finding.line_number,
                fix_code=finding.fix_code or finding.fix_example,
                auto_fix_available=bool(finding.fix_code or finding.fix_example),
                status="open",
                applied_at=None,
                pr_url=None,
                pr_number=None,
                created_at=finding.created_at if finding.created_at else datetime.utcnow(),
                updated_at=finding.created_at if finding.created_at else datetime.utcnow(),
            ))

    # Convert AISuggestion records to response format (handle UUID -> string conversion)
    all_suggestions = [suggestion_to_response(s) for s in suggestions] + finding_suggestions

    return AISuggestionListResponse(
        suggestions=all_suggestions,
        total=len(all_suggestions),
        status_filter=status_filter,
    )


@router.get("/{scan_id}", response_model=AISuggestionListResponse)
async def list_suggestions(
    scan_id: str,
    request: Request,
    status_filter: str | None = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """List AI suggestions for a scan."""
    parse_uuid(scan_id, "scan_id")
    scan_result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = scan_result.scalar_one_or_none()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    await assert_scan_read_access(
        db, scan, current_user, request.headers.get("X-Session-Token")
    )

    # Build query
    query = select(AISuggestion).where(AISuggestion.scan_id == scan_id)

    if status_filter:
        query = query.where(AISuggestion.status == status_filter)

    result = await db.execute(query)
    suggestions = result.scalars().all()

    return AISuggestionListResponse(
        suggestions=[suggestion_to_response(s) for s in suggestions],
        total=len(suggestions),
        status_filter=status_filter,
    )


@router.get("/{suggestion_id}", response_model=AISuggestionResponse)
async def get_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Get a specific AI suggestion."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    suggestion = await _verify_suggestion_ownership(suggestion_id, current_user, db)
    return AISuggestionResponse.model_validate(suggestion)


@router.post("/{suggestion_id}/apply", response_model=ApplyFixResponse)
async def apply_fix(
    suggestion_id: str,
    request: ApplyFixRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
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

    # Get suggestion with ownership verification
    suggestion = await _verify_suggestion_ownership(suggestion_id, current_user, db)

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
    current_user: User | None = Depends(get_optional_user),
):
    """
    Create GitHub PR with fix.
    
    For PRO/ENTERPRISE users only.
    """
    # Check plan gating
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not FeatureGatingService.can_create_pr(current_user):
        ent = resolve_user_entitlements(current_user)
        raise HTTPException(
            status_code=403,
            detail={
                "error": "FEATURE_NOT_AVAILABLE",
                "message": "Create PR is not available on your current plan",
                "current_plan": ent.billing_plan,
                "beta_access_mode": ent.beta_access_mode,
            },
        )

    # Get suggestion with ownership verification
    suggestion = await _verify_suggestion_ownership(suggestion_id, current_user, db)

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
    current_user: User | None = Depends(get_optional_user),
):
    """Mark suggestion as ignored."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    suggestion = await _verify_suggestion_ownership(suggestion_id, current_user, db)
    suggestion.status = SuggestionStatus.IGNORED
    await db.commit()

    return {"success": True, "message": "Suggestion marked as ignored"}


@router.post("/{suggestion_id}/mark-fixed")
async def mark_fixed(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Mark suggestion as fixed."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    suggestion = await _verify_suggestion_ownership(suggestion_id, current_user, db)
    suggestion.status = SuggestionStatus.FIXED
    await db.commit()

    return {"success": True, "message": "Suggestion marked as fixed"}


@router.post("/generate/{finding_id}")
async def generate_suggestion(
    finding_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Generate AI suggestion for a finding."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    parse_uuid(finding_id, "finding_id")
    # Get finding with ownership verification
    result = await db.execute(select(Finding).where(Finding.id == finding_id))
    finding = result.scalar_one_or_none()

    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    # Verify finding belongs to user's scan
    scan_result = await db.execute(
        select(Scan).where(Scan.id == finding.scan_id, Scan.user_id == current_user.id)
    )
    scan = scan_result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if suggestion already exists
    existing = await db.execute(select(AISuggestion).where(AISuggestion.finding_id == finding_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Suggestion already exists for this finding")

    # Generate grounding context + fix via the AI context engine
    # (RAG rule knowledge + MCP live context → LLM), falling back to a
    # deterministic static recommendation when the LLM is unavailable.
    from app.ai.context_engine import AIContextEngine

    fingerprint = hashlib.sha256(
        "|".join(
            [
                str(finding.rule_id or ""),
                str(finding.file_path or ""),
                str(finding.line_number or ""),
            ]
        ).encode("utf-8")
    ).hexdigest()

    engine = AIContextEngine()
    context = await engine.build_context(finding)
    recommendation = await engine.generate_recommendation(finding, context, fingerprint)
    rec = recommendation.to_dict() if hasattr(recommendation, "to_dict") else recommendation

    fix_code = rec.get("fix_code") or rec.get("fix_example") or ""
    if not fix_code and rec.get("full_example"):
        logger.warning(
            "Generated recommendation has only full_example; not storing as auto-apply fix_code",
            finding_id=str(finding_id),
        )
    if not fix_code:
        raise HTTPException(status_code=500, detail="Failed to generate fix")

    # Determine fix_type from file path (informational; not used to gate generation)
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

    # Create suggestion
    suggestion = AISuggestion(
        finding_id=finding_id,
        scan_id=finding.scan_id,
        title=finding.rule_name,
        description=finding.description,
        severity=finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity),
        confidence=float(rec.get("confidence", 0.9)),
        category=finding.category.value if hasattr(finding.category, 'value') else str(finding.category),
        fix_type=fix_type,
        file_path=finding.file_path or "",
        line_number=finding.line_number,
        fix_code=fix_code,
        auto_fix_available=True,
        status=SuggestionStatus.OPEN,
    )

    db.add(suggestion)
    await db.commit()
    await db.refresh(suggestion)

    return {
        "success": True,
        "suggestion_id": str(suggestion.id),
        "fix_code": fix_code,
        "fix_type": fix_type,
        "summary": rec.get("summary", ""),
        "ai_generated": bool(rec.get("ai_generated", False)),
        "source": rec.get("source", "unknown"),
    }


@router.post("/{suggestion_id}/copy-fix")
async def copy_fix(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
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

    # Get suggestion with ownership verification
    suggestion = await _verify_suggestion_ownership(suggestion_id, current_user, db)

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
    current_user: User | None = Depends(get_optional_user),
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

    # Get suggestion with ownership verification
    suggestion = await _verify_suggestion_ownership(suggestion_id, current_user, db)

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
