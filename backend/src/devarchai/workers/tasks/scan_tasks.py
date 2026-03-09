"""Celery tasks for scan execution."""

from celery import states
from typing import Dict, Any
import structlog

from devarchai.workers.celery_app import celery_app
from devarchai.db.session import get_session_factory
from devarchai.models.scan import Scan, ScanStatus
from sqlalchemy import select

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def execute_scan(self, scan_id: str) -> Dict[str, Any]:
    """
    Execute a repository scan.

    Args:
        scan_id: UUID of the scan to execute

    Returns:
        Scan results dictionary
    """
    from devarchai.services.scan_service import ScanService

    try:
        # Update task ID in database
        session_factory = get_session_factory()
        with session_factory() as db:
            result = db.execute(select(Scan).where(Scan.id == scan_id))
            scan = result.scalar_one_or_none()

            if not scan:
                logger.error("Scan not found", scan_id=scan_id)
                return {"status": "failed", "error": "Scan not found"}

            # Update scan with task ID
            scan.celery_task_id = self.request.id
            scan.status = ScanStatus.PROCESSING
            db.commit()

        # Execute scan
        with session_factory() as db:
            scan_service = ScanService(db=db)
            result = db.execute(select(Scan).where(Scan.id == scan_id))
            scan = result.scalar_one_or_none()

            if scan:
                # Run the scan
                updated_scan = scan_service.execute_scan(scan)
                db.commit()

                return {
                    "status": "completed",
                    "scan_id": str(scan.id),
                    "overall_score": updated_scan.overall_score,
                }

    except Exception as exc:
        logger.exception("Scan execution failed", scan_id=scan_id, error=str(exc))

        # Update scan status on error
        session_factory = get_session_factory()
        with session_factory() as db:
            result = db.execute(select(Scan).where(Scan.id == scan_id))
            scan = result.scalar_one_or_none()

            if scan:
                scan.status = ScanStatus.FAILED
                scan.error_message = str(exc)
                db.commit()

        # Re-raise for Celery retry
        raise self.retry(exc=exc)


@celery_app.task(bind=True)
def cancel_scan(self, scan_id: str) -> Dict[str, Any]:
    """
    Cancel a running scan.

    Args:
        scan_id: UUID of the scan to cancel

    Returns:
        Cancellation result
    """
    from devarchai.models.scan import ScanStatus

    session_factory = get_session_factory()
    with session_factory() as db:
        result = db.execute(select(Scan).where(Scan.id == scan_id))
        scan = result.scalar_one_or_none()

        if not scan:
            return {"status": "not_found", "error": "Scan not found"}

        if scan.status not in [ScanStatus.PENDING, ScanStatus.PROCESSING, ScanStatus.QUEUED]:
            return {"status": "already_completed", "message": f"Scan is already {scan.status.value}"}

        # Update status
        scan.status = ScanStatus.CANCELLED
        scan.error_message = "Scan cancelled by user"
        db.commit()

        # Revoke Celery task if running
        if scan.celery_task_id:
            celery_app.control.revoke(scan.celery_task_id, terminate=True)

        return {"status": "cancelled", "scan_id": scan_id}
