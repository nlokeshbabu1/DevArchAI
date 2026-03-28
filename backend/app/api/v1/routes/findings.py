"""Global findings endpoint."""

import structlog
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, get_optional_user
from app.db.session import get_db
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/findings", tags=["Findings"])


@router.get("")
async def list_findings(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all findings for the current user with filtering.
    
    Supports filtering by:
    - severity: critical, high, medium, low, info
    - category: security, reliability, scalability, cost, observability
    - search: Search in rule_name and description
    """
    if not current_user:
        return {
            "findings": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
        }
    
    offset = (page - 1) * page_size
    
    # Get user's scan IDs
    scans_result = await db.execute(
        select(Scan.id).where(Scan.user_id == current_user.id)
    )
    scan_ids = [str(row[0]) for row in scans_result.all()]
    
    if not scan_ids:
        return {
            "findings": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
        }
    
    # Build query
    query = select(Finding).where(Finding.scan_id.in_(scan_ids))
    
    # Apply filters
    if severity:
        query = query.where(Finding.severity == severity.lower())
    
    if category:
        query = query.where(Finding.category == category.lower())
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Finding.rule_name.ilike(search_pattern)) |
            (Finding.description.ilike(search_pattern))
        )
    
    # Get total count before pagination
    count_query = select(Finding.id).where(Finding.scan_id.in_(scan_ids))
    if severity:
        count_query = count_query.where(Finding.severity == severity.lower())
    if category:
        count_query = count_query.where(Finding.category == category.lower())
    if search:
        search_pattern = f"%{search}%"
        count_query = count_query.where(
            (Finding.rule_name.ilike(search_pattern)) |
            (Finding.description.ilike(search_pattern))
        )
    
    total_result = await db.execute(select(func.count()).select_from(count_query.subquery()))
    total = total_result.scalar() or 0
    
    # Apply ordering and pagination
    query = query.order_by(Finding.severity, Finding.created_at.desc())
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    findings = result.scalars().all()

    import json
    return {
        "findings": [
            {
                "id": str(finding.id),
                "scan_id": str(finding.scan_id),
                "rule_id": finding.rule_id,
                "rule_name": finding.rule_name,
                "severity": finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity),
                "category": finding.category.value if hasattr(finding.category, 'value') else str(finding.category),
                "description": finding.description,
                "recommendation": finding.recommendation,
                "file_path": finding.file_path,
                "line_number": finding.line_number,
                "ai_explanation": finding.ai_explanation,
                "ai_generated": finding.ai_generated,
                "summary": finding.summary,
                "risk": finding.risk,
                "impact": finding.impact,
                "fix_code": finding.fix_code,
                "full_example": finding.full_example,
                "best_practices": json.loads(finding.best_practices) if finding.best_practices else [],
                "confidence_score": finding.confidence_score,
                "documentation_url": finding.documentation_url,
                "created_at": finding.created_at.isoformat(),
            }
            for finding in findings
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{finding_id}")
async def get_finding(
    finding_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific finding by ID."""
    from uuid import UUID
    
    try:
        finding_uuid = UUID(finding_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid finding ID format"
        )
    
    # Get finding
    result = await db.execute(
        select(Finding).where(Finding.id == finding_uuid)
    )
    finding = result.scalar_one_or_none()
    
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found"
        )
    
    # Verify user has access to the scan
    scan_result = await db.execute(
        select(Scan).where(
            Scan.id == finding.scan_id,
            Scan.user_id == current_user.id
        )
    )
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return {
        "id": str(finding.id),
        "scan_id": str(finding.scan_id),
        "rule_id": finding.rule_id,
        "rule_name": finding.rule_name,
        "severity": finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity),
        "category": finding.category.value if hasattr(finding.category, 'value') else str(finding.category),
        "description": finding.description,
        "recommendation": finding.recommendation,
        "file_path": finding.file_path,
        "line_number": finding.line_number,
        "ai_explanation": finding.ai_explanation,
        "impact_analysis": finding.impact_analysis,
        "created_at": finding.created_at.isoformat(),
    }


# Import func for count query
from sqlalchemy import func
