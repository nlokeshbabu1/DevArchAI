"""Dashboard routes - Implements missing endpoints."""

from datetime import datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_optional_user
from app.db.session import get_db
from app.models.finding import Finding
from app.models.scan import Scan, ScanStatus
from app.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def get_dashboard_summary(
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get dashboard summary statistics.
    
    Returns aggregated stats for:
    - Total scans
    - Total repositories
    - Total findings
    - Critical findings
    - AI suggestions
    - Average score
    """
    # Get user's scans
    if current_user:
        result = await db.execute(
            select(Scan).where(Scan.user_id == current_user.id)
        )
        scans = result.scalars().all()
    else:
        # For anonymous users, return empty stats
        return {
            "total_scans": 0,
            "total_repositories": 0,
            "total_findings": 0,
            "critical_findings": 0,
            "ai_suggestions": 0,
            "average_score": 0,
        }

    # Get all findings for user's scans
    scan_ids = [str(scan.id) for scan in scans]

    if scan_ids:
        findings_result = await db.execute(
            select(Finding).where(Finding.scan_id.in_(scan_ids))
        )
        findings = findings_result.scalars().all()
    else:
        findings = []

    # Calculate stats
    unique_repos = set(scan.repository_url for scan in scans)
    critical_count = sum(1 for f in findings if f.severity.value == 'critical')
    # Count AI suggestions: findings with ai_generated=true OR ai_explanation present
    ai_suggestions_count = sum(1 for f in findings if f.ai_generated or f.ai_explanation)

    # Calculate average score
    scores = [s.overall_score for s in scans if s.overall_score is not None]
    average_score = sum(scores) / len(scores) if scores else 0

    return {
        "total_scans": len(scans),
        "total_repositories": len(unique_repos),
        "total_findings": len(findings),
        "critical_findings": critical_count,
        "ai_suggestions": ai_suggestions_count,
        "average_score": round(average_score, 2),
    }


@router.get("/recent-scans")
async def get_recent_scans(
    limit: int = Query(default=5, ge=1, le=20),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent scans for dashboard."""
    if not current_user:
        return []

    result = await db.execute(
        select(Scan)
        .where(Scan.user_id == current_user.id)
        .order_by(Scan.created_at.desc())
        .limit(limit)
    )
    scans = result.scalars().all()

    return [
        {
            "id": str(scan.id),
            "repository_url": scan.repository_url,
            "repository_name": scan.repository_url.split("/")[-1].replace(".git", ""),
            "status": scan.status.value,
            "overall_score": scan.overall_score,
            "security_score": scan.security_score,
            "created_at": scan.created_at.isoformat(),
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
            "analysis_duration_seconds": scan.analysis_duration_seconds,
        }
        for scan in scans
    ]


@router.get("/trends")
async def get_score_trends(
    period: str = Query(default="30d", regex="^(7d|30d|90d)$"),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get score trends over time."""
    if not current_user:
        return []

    # Calculate date range
    days = int(period.replace("d", ""))
    start_date = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(Scan)
        .where(
            Scan.user_id == current_user.id,
            Scan.created_at >= start_date,
            Scan.overall_score.isnot(None)
        )
        .order_by(Scan.created_at)
    )
    scans = result.scalars().all()

    # Group by date and calculate averages
    trends = {}
    for scan in scans:
        date_str = scan.created_at.strftime("%Y-%m-%d")
        if date_str not in trends:
            trends[date_str] = {
                "date": date_str,
                "security": 0,
                "scalability": 0,
                "reliability": 0,
                "cost": 0,
                "observability": 0,
                "overall": 0,
                "count": 0,
            }

        trends[date_str]["security"] += scan.security_score or 0
        trends[date_str]["scalability"] += scan.scalability_score or 0
        trends[date_str]["reliability"] += scan.reliability_score or 0
        trends[date_str]["cost"] += scan.cost_score or 0
        trends[date_str]["observability"] += scan.observability_score or 0
        trends[date_str]["overall"] += scan.overall_score or 0
        trends[date_str]["count"] += 1

    # Calculate averages
    result_list = []
    for trend in trends.values():
        count = trend["count"]
        if count > 0:
            result_list.append({
                "date": trend["date"],
                "security": round(trend["security"] / count, 2),
                "scalability": round(trend["scalability"] / count, 2),
                "reliability": round(trend["reliability"] / count, 2),
                "cost": round(trend["cost"] / count, 2),
                "observability": round(trend["observability"] / count, 2),
                "overall": round(trend["overall"] / count, 2),
            })

    return result_list


@router.get("/metrics")
async def get_dashboard_metrics(
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get key metrics for dashboard."""
    if not current_user:
        return {}

    # Get scans
    result = await db.execute(
        select(Scan).where(Scan.user_id == current_user.id)
    )
    scans = result.scalars().all()

    # Get findings
    scan_ids = [str(scan.id) for scan in scans]
    if scan_ids:
        findings_result = await db.execute(
            select(Finding).where(Finding.scan_id.in_(scan_ids))
        )
        findings = findings_result.scalars().all()
    else:
        findings = []

    # Calculate metrics
    severity_counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "info": 0,
    }

    category_counts = {}

    for finding in findings:
        severity = finding.severity.value
        if severity in severity_counts:
            severity_counts[severity] += 1

        category = finding.category.value
        category_counts[category] = category_counts.get(category, 0) + 1

    # Scan status counts
    status_counts = {
        "completed": 0,
        "processing": 0,
        "failed": 0,
        "pending": 0,
    }

    for scan in scans:
        status = scan.status.value
        if status in status_counts:
            status_counts[status] += 1

    return {
        "severity_counts": severity_counts,
        "category_counts": category_counts,
        "status_counts": status_counts,
        "total_scans": len(scans),
        "total_findings": len(findings),
        "completion_rate": round(
            (status_counts["completed"] / len(scans) * 100) if scans else 0, 2
        ),
    }


@router.get("/alerts")
async def get_dashboard_alerts(
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get active alerts for dashboard."""
    if not current_user:
        return []

    alerts = []

    # Get recent failed scans
    result = await db.execute(
        select(Scan)
        .where(
            Scan.user_id == current_user.id,
            Scan.status == ScanStatus.FAILED
        )
        .order_by(Scan.created_at.desc())
        .limit(5)
    )
    failed_scans = result.scalars().all()

    for scan in failed_scans:
        alerts.append({
            "id": f"scan_failed_{scan.id}",
            "type": "scan_failure",
            "severity": "high",
            "title": f"Scan failed for {scan.repository_url.split('/')[-1]}",
            "message": scan.error_message or "Unknown error",
            "created_at": scan.created_at.isoformat(),
            "scan_id": str(scan.id),
        })

    # Get scans with critical findings
    scan_ids = [str(scan.id) for scan in scans] if (scans := (await db.execute(
        select(Scan).where(Scan.user_id == current_user.id, Scan.status == ScanStatus.COMPLETED)
    )).scalars().all()) else []

    if scan_ids:
        critical_findings = await db.execute(
            select(Finding, Finding.scan_id)
            .where(
                Finding.scan_id.in_(scan_ids),
                Finding.severity == "critical"
            )
            .limit(5)
        )

        for finding, scan_id in critical_findings.all():
            alerts.append({
                "id": f"critical_finding_{finding.id}",
                "type": "critical_finding",
                "severity": "critical",
                "title": f"Critical: {finding.rule_name}",
                "message": finding.description,
                "created_at": finding.created_at.isoformat(),
                "scan_id": str(scan_id),
                "finding_id": str(finding.id),
            })

    return alerts
