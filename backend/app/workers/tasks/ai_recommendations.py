"""Celery tasks for the async AI recommendation pipeline.

- ``enqueue_ai_analysis`` — coordinator: creates per-group jobs and dispatches
  parallel workers (one Celery task per deduplicated finding group).
- ``process_finding_ai_job`` — processes a single ``FindingAIJob``.
- ``finalize_scan_ai_analysis`` — chord callback to aggregate scan AI status.
- ``recover_pending_ai_scans`` / ``recover_stale_ai_jobs`` — restart recovery.
"""

from __future__ import annotations

import asyncio
import uuid as uuid_mod
from typing import Any

import structlog
from celery import chord, group
from celery.signals import worker_ready

from app.config import settings
from app.workers.celery_config import celery_app

logger = structlog.get_logger(__name__)

_TASK_COORDINATOR = "app.workers.tasks.ai_recommendations.enqueue_ai_analysis"
_TASK_JOB = "app.workers.tasks.ai_recommendations.process_finding_ai_job"
_TASK_FINALIZE = "app.workers.tasks.ai_recommendations.finalize_scan_ai_analysis"
_TASK_RECOVER_STALE = "app.workers.tasks.ai_recommendations.recover_stale_ai_jobs"


def _run_async_with_isolated_engine(coro_builder: Any) -> Any:
    """Run async work on a dedicated engine/session (safe inside Celery workers)."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    async def _wrapper() -> Any:
        engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=True,
        )
        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        try:
            async with session_factory() as session:
                return await coro_builder(session, session_factory)
        finally:
            await engine.dispose()

    return asyncio.run(_wrapper())


@celery_app.task(
    name=_TASK_COORDINATOR,
    bind=True,
    max_retries=2,
    default_retry_delay=15,
    retry_backoff=True,
    acks_late=True,
    task_track_started=True,
    soft_time_limit=int(getattr(settings, "AI_TASK_MAX_SECONDS", 600)) - 30,
    time_limit=int(getattr(settings, "AI_TASK_MAX_SECONDS", 600)),
)
def enqueue_ai_analysis(
    self: Any,
    scan_id: str,
    force: bool = False,
) -> dict[str, Any]:
    """Create AI jobs for a completed scan and dispatch parallel workers."""
    if not getattr(settings, "AI_RECOMMENDATIONS_ENABLED", True):
        logger.info("AI_RECOMMENDATIONS_DISABLED", scan_id=scan_id)
        _mark_scan_ai_completed(scan_id)
        return {"status": "disabled", "jobs": 0}

    logger.info("AI_RECOMMENDATION_TASK_STARTED", scan_id=scan_id, task_id=self.request.id)
    try:
        job_ids = _prepare_jobs_sync(scan_id, force=force)
        if not job_ids:
            _mark_scan_ai_completed(scan_id)
            return {"status": "completed", "jobs": 0}

        workflow = chord(
            group(process_finding_ai_job.s(str(job_id)) for job_id in job_ids),
            finalize_scan_ai_analysis.s(scan_id),
        )
        workflow.apply_async()
        return {"status": "dispatched", "jobs": len(job_ids)}
    except Exception as exc:
        logger.exception(
            "AI_RECOMMENDATION_COORDINATOR_FAILED",
            scan_id=scan_id,
            error=str(exc),
            task_id=self.request.id,
        )
        _mark_scan_ai_failed(scan_id, str(exc))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=15 * (self.request.retries + 1))
        raise


@celery_app.task(
    name=_TASK_JOB,
    bind=True,
    max_retries=int(getattr(settings, "AI_JOB_MAX_RETRIES", 3)),
    default_retry_delay=int(getattr(settings, "AI_JOB_RETRY_BACKOFF_SECONDS", 30)),
    retry_backoff=True,
    retry_backoff_max=120,
    acks_late=True,
    task_track_started=True,
    soft_time_limit=int(getattr(settings, "AI_TASK_MAX_SECONDS", 600)) - 30,
    time_limit=int(getattr(settings, "AI_TASK_MAX_SECONDS", 600)),
)
def process_finding_ai_job(self: Any, job_id: str) -> dict[str, Any]:
    """Process one ``FindingAIJob`` (idempotent)."""
    logger.info(
        "AI_TASK",
        job_id=job_id,
        task_id=self.request.id,
        status="STARTED",
    )
    try:
        result = _run_job_sync(job_id, celery_task_id=self.request.id)
        logger.info(
            "AI_TASK",
            job_id=job_id,
            task_id=self.request.id,
            status="COMPLETED",
            **{k: result.get(k, 0) for k in ("cache_hits", "llm_calls", "findings_updated")},
        )
        return result
    except Exception as exc:
        logger.exception(
            "AI_TASK",
            job_id=job_id,
            task_id=self.request.id,
            status="FAILED",
            error=str(exc),
            retry_count=self.request.retries,
        )
        if self.request.retries < self.max_retries:
            countdown = int(settings.AI_JOB_RETRY_BACKOFF_SECONDS) * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)
        raise


@celery_app.task(name=_TASK_FINALIZE)
def finalize_scan_ai_analysis(results: list[dict[str, Any]], scan_id: str) -> dict[str, Any]:
    """Aggregate per-job results into scan-level AI status."""
    _finalize_scan_sync(scan_id)
    return {
        "scan_id": scan_id,
        "jobs": len(results or []),
        "findings_updated": sum((r or {}).get("findings_updated", 0) for r in (results or [])),
    }


@celery_app.task(name=_TASK_RECOVER_STALE)
def recover_stale_ai_jobs(limit: int = 50) -> int:
    """Detect and recover AI jobs stuck in non-terminal states."""
    return _recover_stale_sync(limit=limit)


def _prepare_jobs_sync(scan_id: str, force: bool = False) -> list[str]:
    from app.services.ai_job_service import ensure_jobs_for_scan

    async def _runner(session: Any, _session_factory: Any) -> list[str]:
        from app.models.scan import Scan

        if not force:
            scan = await session.get(Scan, uuid_mod.UUID(scan_id))
            if scan is None:
                raise ValueError(f"Scan not found: {scan_id}")
            if scan.ai_status == "completed":
                logger.info(
                    "AI_RECOMMENDATION_SKIP_ALREADY_DONE",
                    scan_id=scan_id,
                    ai_status=scan.ai_status,
                )
                return []
        jobs = await ensure_jobs_for_scan(session, scan_id, force=force)
        return [str(job.id) for job in jobs]

    return _run_async_with_isolated_engine(_runner)


def _run_job_sync(job_id: str, celery_task_id: str | None = None) -> dict[str, Any]:
    from app.services.ai_recommendation_service import AIRecommendationService

    async def _runner(session: Any, session_factory: Any) -> dict[str, Any]:
        service = AIRecommendationService(
            session=session,
            session_factory=session_factory,
        )
        return await service.process_job(job_id, celery_task_id=celery_task_id)

    return _run_async_with_isolated_engine(_runner)


def _finalize_scan_sync(scan_id: str) -> None:
    from app.services.ai_job_service import aggregate_scan_ai_status

    async def _runner(session: Any, _session_factory: Any) -> None:
        await aggregate_scan_ai_status(session, scan_id)

    _run_async_with_isolated_engine(_runner)


def _recover_stale_sync(limit: int = 50) -> int:
    from app.services.ai_job_service import recover_stale_jobs

    async def _runner(session: Any, _session_factory: Any) -> tuple[int, list[str]]:
        return await recover_stale_jobs(session, limit=limit)

    count, job_ids = _run_async_with_isolated_engine(_runner)
    for job_id in job_ids:
        process_finding_ai_job.delay(job_id)
    if job_ids:
        logger.info("AI_JOBS_REDISPATCHED", count=len(job_ids), job_ids=job_ids[:10])
    if count:
        recover_pending_ai_scans(limit=limit)
    return count


def _mark_scan_ai_completed(scan_id: str) -> None:
    from datetime import UTC, datetime

    from app.models.scan import Scan
    from sqlalchemy import select

    from app.db.session import get_sync_session_factory

    session = get_sync_session_factory()()
    try:
        scan = session.execute(
            select(Scan).where(Scan.id == uuid_mod.UUID(scan_id))
        ).scalar_one_or_none()
        if scan and scan.ai_status not in ("completed", "processing"):
            scan.ai_status = "completed"
            scan.ai_completed_at = datetime.now(UTC)
            scan.ai_error_message = None
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def _mark_scan_ai_failed(scan_id: str, error: str) -> None:
    from app.models.scan import Scan
    from sqlalchemy import select

    from app.db.session import get_sync_session_factory

    session = get_sync_session_factory()()
    try:
        scan = session.execute(
            select(Scan).where(Scan.id == uuid_mod.UUID(scan_id))
        ).scalar_one_or_none()
        if scan and scan.ai_status not in ("completed",):
            scan.ai_status = "failed"
            scan.ai_error_message = error[:1000]
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def recover_pending_ai_scans(limit: int | None = None) -> int:
    """Re-enqueue scans stuck in ``pending`` or ``queued`` (restart recovery)."""
    from app.models.scan import Scan
    from sqlalchemy import select

    from app.db.session import get_sync_session_factory

    pending_ids: list[str] = []
    session = get_sync_session_factory()()
    try:
        query = (
            select(Scan.id)
            .where(Scan.ai_status.in_(("pending", "queued")))
            .order_by(Scan.created_at.asc())
        )
        if limit:
            query = query.limit(limit)
        pending_ids = [str(scan_id) for scan_id in session.execute(query).scalars().all()]
    finally:
        session.close()

    for scan_id in pending_ids:
        from app.services.ai_recommendation_service import enqueue_ai_analysis_for_scan

        enqueue_ai_analysis_for_scan(scan_id)

    if pending_ids:
        logger.info("AI_RECOMMENDATION_RECOVERED", count=len(pending_ids), scans=pending_ids)
    return len(pending_ids)


@worker_ready.connect
def _on_worker_ready(sender: Any = None, **kwargs: Any) -> None:
    """After the worker starts, resume AI analysis for interrupted scans."""
    try:
        recover_pending_ai_scans()
        recover_stale_ai_jobs.delay()
    except Exception as exc:
        logger.warning("AI_RECOMMENDATION_RECOVERY_FAILED", error=str(exc))
