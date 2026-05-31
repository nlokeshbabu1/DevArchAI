"""Report routes backed by stored S3 artifacts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user, get_optional_user
from app.db.session import get_db
from app.models.anonymous_scan import AnonymousScan
from app.models.report import Report
from app.models.scan import Scan
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.report import (
    ReportDownloadResponse,
    ReportListResponse,
    ReportResponse,
    ReportSummary,
)
from app.services.report_service import (
    ReportService,
    build_download_expiry,
    normalize_report_format,
)
from app.services.report_storage import PRESIGNED_URL_EXPIRY_SECONDS

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])


def _parse_uuid(value: str, field_name: str) -> UUID:
    """Parse a UUID path parameter and return a 400 on invalid input."""
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format: {value}. Expected UUID.",
        ) from exc


async def _get_owned_report(
    *,
    db: AsyncSession,
    report_id: UUID,
    user_id: UUID,
) -> Report | None:
    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .where(Report.id == report_id, Scan.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def _get_accessible_scan_for_download(
    *,
    db: AsyncSession,
    scan_id: UUID,
    current_user: User | None,
    session_token: str | None,
) -> Scan:
    result = await db.execute(
        select(Scan)
        .options(selectinload(Scan.report))
        .where(Scan.id == scan_id)
    )
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    if scan.user_id:
        if not current_user or scan.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you do not own this scan",
            )
        return scan

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A valid session token is required for anonymous scan downloads",
        )

    anonymous_result = await db.execute(
        select(AnonymousScan).where(
            AnonymousScan.linked_scan_id == str(scan.id),
            AnonymousScan.session_token == session_token,
            AnonymousScan.expires_at > datetime.utcnow(),
        )
    )
    anonymous_scan = anonymous_result.scalar_one_or_none()

    if not anonymous_scan:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anonymous scan session is invalid or expired",
        )

    return scan


@router.get("", response_model=ReportListResponse)
async def list_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all reports for the current user."""
    offset = (page - 1) * page_size

    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .where(Scan.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    reports = result.scalars().all()

    total = await db.scalar(
        select(func.count(Report.id))
        .join(Scan, Report.scan_id == Scan.id)
        .where(Scan.user_id == current_user.id)
    )

    return ReportListResponse(
        reports=[ReportResponse.model_validate(report) for report in reports],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/scan/{scan_id}/latest", response_model=ReportResponse)
async def get_latest_report_for_scan(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the report associated with a scan."""
    scan_uuid = _parse_uuid(scan_id, "scan_id")

    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .where(Scan.id == scan_uuid, Scan.user_id == current_user.id)
        .order_by(Report.created_at.desc())
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No report found for this scan",
        )

    return report


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific report."""
    report_uuid = _parse_uuid(report_id, "report_id")
    report = await _get_owned_report(db=db, report_id=report_uuid, user_id=current_user.id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return report


@router.get("/{scan_id}/download", response_model=ReportDownloadResponse)
async def download_report(
    scan_id: str,
    format: str = Query(default="pdf"),
    session_token: str | None = Query(default=None),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a short-lived presigned URL for a stored PDF or Excel report."""
    scan_uuid = _parse_uuid(scan_id, "scan_id")

    try:
        normalized_format = normalize_report_format(format)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    scan = await _get_accessible_scan_for_download(
        db=db,
        scan_id=scan_uuid,
        current_user=current_user,
        session_token=session_token,
    )
    report = scan.report

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    report_service = ReportService()
    try:
        download_url = report_service.generate_download_url(
            report=report,
            scan=scan,
            format=normalized_format,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception(
            "Failed to generate presigned report URL",
            scan_id=scan_id,
            format=normalized_format,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report download URL",
        ) from exc

    extension = "pdf" if normalized_format == "pdf" else "xlsx"
    return ReportDownloadResponse(
        report_id=report.id,
        scan_id=scan.id,
        format=normalized_format,
        url=download_url,
        filename=f"report_{scan.id}.{extension}",
        expires_at=build_download_expiry(),
        expires_in_seconds=PRESIGNED_URL_EXPIRY_SECONDS,
    )


@router.get("/{report_id}/summary", response_model=ReportSummary)
async def get_report_summary(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a brief summary of a report."""
    report_uuid = _parse_uuid(report_id, "report_id")
    report = await _get_owned_report(db=db, report_id=report_uuid, user_id=current_user.id)

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
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a report record."""
    report_uuid = _parse_uuid(report_id, "report_id")
    report = await _get_owned_report(db=db, report_id=report_uuid, user_id=current_user.id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    await db.delete(report)
    await db.commit()

    return MessageResponse(message="Report deleted successfully")
