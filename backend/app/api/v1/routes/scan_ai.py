"""AI recommendation status API routes for repository scans."""

from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user, get_optional_user
from app.core.scan_access import assert_scan_read_access
from app.db.session import get_db
from app.models.finding import Finding
from app.models.finding_ai_job import FindingAIJob
from app.models.scan import Scan
from app.models.user import User
from app.services.ai_job_service import serialize_job, source_display, summarize_scan_ai
from app.services.ai_source_provenance import (
    documentation_status_display,
    normalize_sources,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/scans", tags=["Scan AI"])


def _parse_uuid(value: str, label: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {label}: {value}",
        ) from exc


async def _get_scan_or_404(scan_id: str, db: AsyncSession) -> Scan:
    scan_uuid = _parse_uuid(scan_id, "scan_id")
    scan = await db.get(Scan, scan_uuid)
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return scan


async def _verify_scan_access(
    db: AsyncSession,
    scan: Scan,
    user: User | None,
    session_token: str | None,
) -> None:
    await assert_scan_read_access(db, scan, user, session_token)


@router.get("/{scan_id}/ai/status")
async def get_scan_ai_status(
    scan_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Return aggregate AI recommendation status for a scan."""
    scan = await _get_scan_or_404(scan_id, db)
    await _verify_scan_access(db, scan, current_user, request.headers.get("X-Session-Token"))
    summary = await summarize_scan_ai(db, scan.id)
    return summary


@router.get("/{scan_id}/ai")
async def get_scan_ai_recommendations(
    scan_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Return per-job AI recommendations for a scan."""
    scan = await _get_scan_or_404(scan_id, db)
    await _verify_scan_access(db, scan, current_user, request.headers.get("X-Session-Token"))
    jobs = (
        await db.execute(
            select(FindingAIJob)
            .where(FindingAIJob.scan_id == scan.id)
            .order_by(FindingAIJob.created_at.asc())
        )
    ).scalars().all()
    return {
        "scan_id": str(scan.id),
        "ai_status": scan.ai_status,
        "jobs": [serialize_job(job) for job in jobs],
    }


@router.get("/{scan_id}/ai/findings")
async def get_scan_ai_findings(
    scan_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Map each finding to its AI job status (for CLI/UI per-finding display)."""
    scan = await _get_scan_or_404(scan_id, db)
    await _verify_scan_access(db, scan, current_user, request.headers.get("X-Session-Token"))
    jobs = (
        await db.execute(select(FindingAIJob).where(FindingAIJob.scan_id == scan.id))
    ).scalars().all()

    finding_map: dict[str, dict] = {}
    for job in jobs:
        payload = serialize_job(job)
        for finding_id in job.finding_ids or []:
            finding_map[str(finding_id)] = {
                "finding_id": str(finding_id),
                "job_id": str(job.id),
                "rule_id": job.rule_id,
                "technology": job.technology,
                "status": job.status,
                "source": job.source,
                "source_display": source_display(job.source),
                "documentation_status": job.documentation_status,
                "documentation_status_display": documentation_status_display(
                    job.documentation_status
                ),
                "sources": normalize_sources(job.sources),
                "error_message": job.error_message,
                "recommendation": job.recommendation,
            }
    return {
        "scan_id": str(scan.id),
        "ai_status": scan.ai_status,
        "findings": finding_map,
        "jobs": [payload for payload in (serialize_job(j) for j in jobs)],
    }


@router.get("/ai/diagnostics/stale-jobs")
async def get_stale_ai_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin diagnostic: list AI jobs that appear stuck (non-terminal, aged)."""
    from datetime import UTC, datetime, timedelta

    from app.config import settings

    now = datetime.now(UTC)
    queued_cutoff = now - timedelta(seconds=int(settings.AI_JOB_QUEUED_STALE_SECONDS))
    stale_cutoff = now - timedelta(seconds=int(settings.AI_JOB_STALE_SECONDS))

    jobs = (
        await db.execute(
            select(FindingAIJob)
            .where(
                FindingAIJob.status.notin_(["completed", "failed"]),
                FindingAIJob.scan_id.in_(
                    select(Scan.id).where(Scan.user_id == current_user.id)
                ),
            )
        )
    ).scalars().all()

    stale = []
    for job in jobs:
        updated = job.updated_at or job.created_at
        if not updated:
            continue
        age = (now - updated).total_seconds()
        threshold = (
            int(settings.AI_JOB_QUEUED_STALE_SECONDS)
            if job.status in ("queued", "not_started")
            else int(settings.AI_JOB_STALE_SECONDS)
        )
        if age >= threshold:
            stale.append({**serialize_job(job), "age_seconds": int(age), "threshold_seconds": threshold})

    return {"stale_jobs": stale, "count": len(stale), "checked_at": now.isoformat()}


findings_router = APIRouter(prefix="/findings", tags=["Finding AI"])


@findings_router.get("/{finding_id}/recommendation")
async def get_finding_recommendation(
    finding_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Return AI recommendation status and payload for a single finding."""
    finding_uuid = _parse_uuid(finding_id, "finding_id")
    finding = (
        await db.execute(
            select(Finding).where(Finding.id == finding_uuid).options(selectinload(Finding.scan))
        )
    ).scalar_one_or_none()
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    scan = finding.scan
    if scan:
        await _verify_scan_access(
            db, scan, current_user, request.headers.get("X-Session-Token")
        )

    job = None
    jobs = (
        await db.execute(select(FindingAIJob).where(FindingAIJob.scan_id == finding.scan_id))
    ).scalars().all()
    for candidate in jobs:
        if str(finding.id) in (candidate.finding_ids or []):
            job = candidate
            break

    return {
        "finding_id": str(finding.id),
        "scan_id": str(finding.scan_id),
        "rule_id": finding.rule_id,
        "ai_generated": finding.ai_generated,
        "summary": finding.summary,
        "risk": finding.risk,
        "impact": finding.impact,
        "fix_code": finding.fix_code,
        "fix_example": finding.fix_example,
        "full_example": finding.full_example,
        "best_practices": finding.best_practices,
        "documentation_url": finding.documentation_url,
        "documentation_status": job.documentation_status if job else None,
        "documentation_status_display": documentation_status_display(
            job.documentation_status if job else None
        ),
        "sources": normalize_sources(job.sources) if job else [],
        "job": serialize_job(job) if job else None,
    }
