"""Finding AI job lifecycle — create, track, aggregate, and recover stale jobs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import func, select, update

from app.config import settings
from app.models.finding import Finding
from app.models.finding_ai_job import FindingAIJob, FindingAIJobStatus, SOURCE_DISPLAY
from app.models.scan import Scan
from app.services.ai_recommendation_cache import (
    config_digest,
    context_versions,
    finding_fingerprint,
    recommendation_cache_key,
)
from app.services.ai_eligibility import (
    filter_ai_eligible_findings,
    finding_severity_value,
    is_ai_eligible_finding,
)
from app.services.ai_source_provenance import (
    documentation_status_display,
    normalize_sources,
)

logger = structlog.get_logger(__name__)

TERMINAL_STATUSES = {
    FindingAIJobStatus.COMPLETED.value,
    FindingAIJobStatus.FAILED.value,
}


def source_display(source: str | None) -> str | None:
    if not source:
        return None
    normalized = source.lower()
    if normalized in ("llm", "rag"):
        return SOURCE_DISPLAY.get("rag", normalized)
    if normalized in ("mcp", "live"):
        return SOURCE_DISPLAY.get("mcp", normalized)
    if "mcp" in normalized and "rag" in normalized:
        return SOURCE_DISPLAY["rag_mcp"]
    return SOURCE_DISPLAY.get(normalized, source)


async def build_job_groups(
    session: Any,
    scan: Scan,
    *,
    max_per_scan: int | None = None,
    context_engine: Any | None = None,
) -> list[dict[str, Any]]:
    """Group findings by deterministic cache key for idempotent AI jobs."""
    from app.ai.context_engine import AIContextEngine

    engine = context_engine or AIContextEngine()
    limit = max_per_scan or int(getattr(settings, "AI_RECOMMENDATIONS_MAX_PER_SCAN", 50) or 50)
    all_findings = (
        (
            await session.execute(
                select(Finding)
                .where(Finding.scan_id == scan.id)
                .order_by(Finding.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    eligible = filter_ai_eligible_findings(all_findings)
    findings = eligible[:limit]
    if not findings:
        return []

    config_digest_value = config_digest(
        (scan.detected_stack or []) if isinstance(scan.detected_stack, list) else None
    )
    versions = context_versions()

    groups: dict[str, dict[str, Any]] = {}
    for finding in findings:
        tech = engine.technology_for_finding(finding)
        fingerprint = finding_fingerprint(finding)
        rule_id = str(getattr(finding, "rule_id", "") or "")
        key = recommendation_cache_key(rule_id, tech, fingerprint, config_digest_value, versions)
        bucket = groups.setdefault(
            key,
            {
                "cache_key": key,
                "rule_id": rule_id,
                "technology": tech,
                "finding_ids": [],
                "representative_finding_id": str(finding.id),
            },
        )
        bucket["finding_ids"].append(str(finding.id))

    return list(groups.values())


async def ensure_jobs_for_scan(
    session: Any,
    scan_id: UUID | str,
    *,
    force: bool = False,
    max_per_scan: int | None = None,
    context_engine: Any | None = None,
) -> list[FindingAIJob]:
    """Create ``FindingAIJob`` rows for a scan (idempotent). Returns pending jobs."""
    scan_uuid = scan_id if isinstance(scan_id, UUID) else UUID(str(scan_id))
    scan = await session.get(Scan, scan_uuid)
    if scan is None:
        raise ValueError(f"Scan not found: {scan_id}")

    existing = (
        await session.execute(
            select(FindingAIJob).where(FindingAIJob.scan_id == scan_uuid)
        )
    ).scalars().all()
    if existing and not force:
        return [job for job in existing if not job.is_terminal]

    if force and existing:
        for job in existing:
            await session.delete(job)
        await session.flush()

    groups = await build_job_groups(
        session,
        scan,
        max_per_scan=max_per_scan,
        context_engine=context_engine,
    )
    created: list[FindingAIJob] = []
    for group in groups:
        job = FindingAIJob(
            scan_id=scan_uuid,
            cache_key=group["cache_key"],
            representative_finding_id=UUID(group["representative_finding_id"]),
            finding_ids=group["finding_ids"],
            rule_id=group["rule_id"],
            technology=group["technology"],
            status=FindingAIJobStatus.QUEUED.value,
        )
        session.add(job)
        created.append(job)

    if scan.ai_status in (None, "pending", "failed"):
        scan.ai_status = "queued"
    scan.ai_error_message = None
    await session.commit()
    for job in created:
        await session.refresh(job)
    return created


async def set_job_status(
    session: Any,
    job_id: UUID | str,
    status: FindingAIJobStatus | str,
    *,
    source: str | None = None,
    error_message: str | None = None,
    recommendation: dict | None = None,
    celery_task_id: str | None = None,
    sources: list[dict] | None = None,
    documentation_status: str | None = None,
) -> FindingAIJob | None:
    job_uuid = job_id if isinstance(job_id, UUID) else UUID(str(job_id))
    job = await session.get(FindingAIJob, job_uuid)
    if job is None:
        return None

    status_value = status.value if isinstance(status, FindingAIJobStatus) else str(status)
    now = datetime.now(UTC)
    job.status = status_value
    job.updated_at = now
    if source is not None:
        job.source = source
    if error_message is not None:
        job.error_message = error_message[:1000]
    if recommendation is not None:
        job.recommendation = recommendation
    if sources is not None:
        job.sources = sources
    if documentation_status is not None:
        job.documentation_status = documentation_status
    if celery_task_id is not None:
        job.celery_task_id = celery_task_id
    if status_value == FindingAIJobStatus.GENERATING.value and job.started_at is None:
        job.started_at = now
    if status_value in TERMINAL_STATUSES:
        job.completed_at = now

    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def aggregate_scan_ai_status(session: Any, scan_id: UUID | str) -> str:
    """Recompute scan-level ``ai_status`` from per-job states."""
    scan_uuid = scan_id if isinstance(scan_id, UUID) else UUID(str(scan_id))
    scan = await session.get(Scan, scan_uuid)
    if scan is None:
        return "failed"

    rows = (
        await session.execute(
            select(FindingAIJob.status, func.count())
            .where(FindingAIJob.scan_id == scan_uuid)
            .group_by(FindingAIJob.status)
        )
    ).all()
    if not rows:
        scan.ai_status = "completed"
        scan.ai_completed_at = datetime.now(UTC)
        await session.commit()
        return scan.ai_status

    counts = {status: count for status, count in rows}
    total = sum(counts.values())
    completed = counts.get(FindingAIJobStatus.COMPLETED.value, 0)
    failed = counts.get(FindingAIJobStatus.FAILED.value, 0)
    terminal = completed + failed

    if terminal == total:
        scan.ai_status = "completed" if failed < total else "failed"
        scan.ai_completed_at = datetime.now(UTC)
        if failed == total:
            scan.ai_error_message = "All AI recommendation jobs failed"
        else:
            scan.ai_error_message = None
    elif counts.get(FindingAIJobStatus.QUEUED.value, 0) == total:
        scan.ai_status = "queued"
    else:
        scan.ai_status = "processing"

    await session.commit()
    return scan.ai_status


def serialize_job(job: FindingAIJob) -> dict[str, Any]:
    return {
        "id": str(job.id),
        "scan_id": str(job.scan_id),
        "finding_ids": job.finding_ids or [],
        "representative_finding_id": str(job.representative_finding_id),
        "rule_id": job.rule_id,
        "technology": job.technology,
        "status": job.status,
        "source": job.source,
        "source_display": source_display(job.source),
        "documentation_status": job.documentation_status,
        "documentation_status_display": documentation_status_display(job.documentation_status),
        "sources": normalize_sources(job.sources),
        "recommendation": job.recommendation,
        "model": job.model,
        "prompt_version": job.prompt_version,
        "rag_context_version": job.rag_context_version,
        "retry_count": job.retry_count,
        "error_message": job.error_message,
        "celery_task_id": job.celery_task_id,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


async def summarize_scan_ai(session: Any, scan_id: UUID | str) -> dict[str, Any]:
    scan_uuid = scan_id if isinstance(scan_id, UUID) else UUID(str(scan_id))
    scan = await session.get(Scan, scan_uuid)
    jobs = (
        await session.execute(
            select(FindingAIJob).where(FindingAIJob.scan_id == scan_uuid).order_by(FindingAIJob.created_at)
        )
    ).scalars().all()

    by_status: dict[str, int] = {}
    for job in jobs:
        by_status[job.status] = by_status.get(job.status, 0) + 1

    findings_rows = (
        await session.execute(select(Finding).where(Finding.scan_id == scan_uuid))
    ).scalars().all()
    total_findings = len(findings_rows)
    eligible_findings = filter_ai_eligible_findings(findings_rows)
    info_excluded = sum(1 for f in findings_rows if finding_severity_value(f) == "info")
    low_excluded = sum(
        1 for f in findings_rows if finding_severity_value(f) == "low" and not is_ai_eligible_finding(f)
    )
    jobs_completed = by_status.get(FindingAIJobStatus.COMPLETED.value, 0)
    jobs_failed = by_status.get(FindingAIJobStatus.FAILED.value, 0)

    return {
        "scan_id": str(scan_uuid),
        "ai_status": scan.ai_status if scan else "unknown",
        "ai_error_message": scan.ai_error_message if scan else None,
        "total_jobs": len(jobs),
        "by_status": by_status,
        "jobs": [serialize_job(job) for job in jobs],
        "total_findings": total_findings,
        "ai_eligible_findings": len(eligible_findings),
        "info_excluded_count": info_excluded,
        "low_excluded_count": low_excluded,
        "jobs_analyzed": jobs_completed + jobs_failed,
        "jobs_eligible_total": len(jobs),
    }


async def recover_stale_jobs(session: Any, *, limit: int = 50) -> tuple[int, list[str]]:
    """Mark or re-queue AI jobs that have not progressed within configured thresholds."""
    now = datetime.now(UTC)
    queued_cutoff = now - timedelta(seconds=int(settings.AI_JOB_QUEUED_STALE_SECONDS))
    stale_cutoff = now - timedelta(seconds=int(settings.AI_JOB_STALE_SECONDS))

    stale_jobs = (
        await session.execute(
            select(FindingAIJob)
            .where(
                FindingAIJob.status.in_(
                    [
                        FindingAIJobStatus.QUEUED.value,
                        FindingAIJobStatus.NOT_STARTED.value,
                    ]
                ),
                FindingAIJob.updated_at < queued_cutoff,
            )
            .limit(limit)
        )
    ).scalars().all()

    stuck_jobs = (
        await session.execute(
            select(FindingAIJob)
            .where(
                FindingAIJob.status.in_(
                    [
                        FindingAIJobStatus.CHECKING_CACHE.value,
                        FindingAIJobStatus.RAG_RETRIEVING.value,
                        FindingAIJobStatus.MCP_RETRIEVING.value,
                        FindingAIJobStatus.GENERATING.value,
                        FindingAIJobStatus.SAVING.value,
                        FindingAIJobStatus.RETRYING.value,
                    ]
                ),
                FindingAIJob.updated_at < stale_cutoff,
            )
            .limit(limit)
        )
    ).scalars().all()

    recovered = 0
    for job in stale_jobs + stuck_jobs:
        if job.retry_count >= int(settings.AI_JOB_MAX_RETRIES):
            job.status = FindingAIJobStatus.FAILED.value
            job.error_message = "AI job exceeded maximum retries (stale detection)"
            job.completed_at = now
        else:
            job.status = FindingAIJobStatus.RETRYING.value
            job.retry_count = (job.retry_count or 0) + 1
            job.error_message = "Recovered from stale state; scheduled for retry"
        job.updated_at = now
        session.add(job)
        recovered += 1

    if recovered:
        await session.commit()
        logger.warning("AI_JOBS_RECOVERED_STALE", count=recovered)

    redispatch_ids = [str(job.id) for job in stale_jobs + stuck_jobs if job.status != FindingAIJobStatus.FAILED.value]
    return recovered, redispatch_ids
