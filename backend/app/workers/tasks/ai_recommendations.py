"""Celery task for the async AI recommendation pipeline.

The scanner commits ``COMPLETED`` before this job is enqueued, so the result
page opens immediately; AI analysis runs here, asynchronously, with zero
added scan latency.

- ``enqueue_ai_analysis`` — the pipeline entry point for a scan.
- ``recover_pending_ai_scans`` — restart recovery: re-enqueues scans that were
  left in ``pending`` by a crashed worker.
"""

from __future__ import annotations

import asyncio
import uuid as uuid_mod
from typing import Any

import structlog
from celery.signals import worker_ready

from app.config import settings
from app.workers.celery_config import celery_app

logger = structlog.get_logger(__name__)

_TASK_NAME = "app.workers.tasks.ai_recommendations.enqueue_ai_analysis"


@celery_app.task(
    name=_TASK_NAME,
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    retry_backoff=True,
    retry_backoff_max=120,
    acks_late=True,
    task_track_started=True,
)
def enqueue_ai_analysis(
    self: Any,
    scan_id: str,
    force: bool = False,
) -> None:
    """Run the AI recommendation pipeline for a completed scan."""
    if not getattr(settings, "AI_RECOMMENDATIONS_ENABLED", True):
        logger.info("AI_RECOMMENDATIONS_DISABLED", scan_id=scan_id)
        _mark_scan_ai_completed(scan_id)
        return

    logger.info("AI_RECOMMENDATION_TASK_STARTED", scan_id=scan_id)
    try:
        _run_pipeline_sync(scan_id, force=force)
    except Exception as exc:
        logger.exception(
            "AI_RECOMMENDATION_TASK_FAILED",
            scan_id=scan_id,
            error=str(exc),
            task_id=self.request.id,
        )
        _mark_scan_ai_failed(scan_id, str(exc))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=15 * (self.request.retries + 1))
        raise


def _run_pipeline_sync(scan_id: str, force: bool = False) -> None:
    """Run the async pipeline inside a fresh event loop + DB session."""
    from app.services.ai_recommendation_service import run_ai_recommendations_for_scan

    async def _runner():
        if not force:
            from app.models.scan import Scan
            from sqlalchemy import select
            from app.db.session import get_session_factory
            from sqlalchemy.orm import selectinload

            # Load the scan first to apply the idempotency guard cheaply.
            async with get_session_factory()() as session:
                scan = (
                    await session.execute(
                        select(Scan)
                        .where(Scan.id == uuid_mod.UUID(scan_id))
                        .options(selectinload(Scan.findings))
                    )
                ).scalar_one_or_none()
                if scan is None:
                    raise ValueError(f"Scan not found: {scan_id}")
                if scan.ai_status == "completed":
                    logger.info(
                        "AI_RECOMMENDATION_SKIP_ALREADY_DONE",
                        scan_id=scan_id,
                        ai_status=scan.ai_status,
                    )
                    return None
        return await run_ai_recommendations_for_scan(scan_id)

    asyncio.run(_runner())


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
    """Re-enqueue scans stuck in ``pending`` (restart recovery). Returns count."""
    from app.models.scan import Scan
    from sqlalchemy import select

    from app.db.session import get_sync_session_factory

    pending_ids: list[str] = []
    session = get_sync_session_factory()()
    try:
        query = (
            select(Scan.id)
            .where(Scan.ai_status == "pending")
            .order_by(Scan.created_at.asc())
        )
        if limit:
            query = query.limit(limit)
        pending_ids = [str(row.id) for row in session.execute(query).scalars().all()]
    finally:
        session.close()

    for scan_id in pending_ids:
        enqueue_ai_analysis.delay(scan_id)

    if pending_ids:
        logger.info("AI_RECOMMENDATION_RECOVERED", count=len(pending_ids), scans=pending_ids)
    return len(pending_ids)


@worker_ready.connect
def _on_worker_ready(sender: Any = None, **kwargs: Any) -> None:
    """After the worker starts, resume AI analysis for interrupted scans."""
    try:
        recover_pending_ai_scans()
    except Exception as exc:
        logger.warning("AI_RECOMMENDATION_RECOVERY_FAILED", error=str(exc))
