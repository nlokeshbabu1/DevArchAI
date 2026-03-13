"""Report routes."""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.finding import Finding
from app.models.report import Report
from app.models.scan import Scan
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.report import (
    ReportListResponse,
    ReportResponse,
    ReportSummary,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", response_model=ReportListResponse)
async def list_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all reports for the current user."""
    offset = (page - 1) * page_size

    # Get reports joined with scans to filter by user
    query = (
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .where(Scan.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    reports = result.scalars().all()

    # Get total count
    count_query = (
        select(func.count(Report.id))
        .join(Scan, Report.scan_id == Scan.id)
        .where(Scan.user_id == current_user.id)
    )
    total = await db.scalar(count_query)

    return ReportListResponse(
        reports=[ReportResponse.model_validate(report) for report in reports],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific report."""
    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .where(Report.id == report_id, Scan.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return report


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    format: str = Query(default="json", regex="^(json|csv)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a report in JSON or CSV format."""
    # Get report
    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .where(Report.id == report_id, Scan.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    if format == "json":
        # Get findings for the report
        findings_result = await db.execute(
            select(Finding).where(Finding.scan_id == report.scan_id)
        )
        findings = findings_result.scalars().all()

        # Build complete report
        report_data = {
            "report": {
                "id": report.id,
                "scan_id": report.scan_id,
                "repository_name": report.repository_name,
                "repository_url": report.repository_url,
                "commit_hash": report.commit_hash,
                "created_at": report.created_at.isoformat(),
                "overall_score": report.overall_score,
                "category_scores": report.category_scores,
                "executive_summary": report.executive_summary,
                "risk_analysis": report.risk_analysis,
                "prioritized_recommendations": report.prioritized_recommendations,
                "summary": {
                    "total_findings": report.total_findings,
                    "critical": report.critical_count,
                    "high": report.high_count,
                    "medium": report.medium_count,
                    "low": report.low_count,
                    "info": report.info_count,
                },
                "files_analyzed": report.files_analyzed,
            },
            "findings": [
                {
                    "id": f.id,
                    "rule_id": f.rule_id,
                    "rule_name": f.rule_name,
                    "severity": f.severity.value,
                    "category": f.category.value,
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "file_path": f.file_path,
                    "line_number": f.line_number,
                    "ai_explanation": f.ai_explanation,
                    "impact_analysis": f.impact_analysis,
                }
                for f in findings
            ],
        }

        return JSONResponse(
            content=report_data,
            headers={
                "Content-Disposition": f'attachment; filename="report_{report_id}.json"'
            },
        )

    elif format == "csv":
        # Get findings for CSV export
        findings_result = await db.execute(
            select(Finding).where(Finding.scan_id == report.scan_id)
        )
        findings = findings_result.scalars().all()

        # Build CSV
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Rule ID",
            "Rule Name",
            "Severity",
            "Category",
            "Description",
            "Recommendation",
            "File Path",
            "Line Number",
        ])

        # Rows
        for finding in findings:
            writer.writerow([
                finding.rule_id,
                finding.rule_name,
                finding.severity.value,
                finding.category.value,
                finding.description,
                finding.recommendation,
                finding.file_path or "",
                finding.line_number or "",
            ])

        return JSONResponse(
            content={"csv": output.getvalue()},
            headers={
                "Content-Disposition": f'attachment; filename="report_{report_id}.csv"'
            },
        )


@router.get("/{report_id}/summary", response_model=ReportSummary)
async def get_report_summary(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a brief summary of a report."""
    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .where(Report.id == report_id, Scan.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return ReportSummary(
        id=report.id,
        scan_id=report.scan_id,
        repository_name=report.repository_name,
        overall_score=report.overall_score,
        total_findings=report.total_findings,
        critical_count=report.critical_count,
        high_count=report.high_count,
        created_at=report.created_at,
    )


@router.delete("/{report_id}", response_model=MessageResponse)
async def delete_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a report."""
    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .where(Report.id == report_id, Scan.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    await db.delete(report)
    await db.commit()

    return MessageResponse(message="Report deleted successfully")


@router.get("/scan/{scan_id}/latest", response_model=ReportResponse)
async def get_latest_report_for_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the latest report for a scan."""
    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .where(Scan.id == scan_id, Scan.user_id == current_user.id)
        .order_by(Report.created_at.desc())
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No report found for this scan",
        )

    return report
