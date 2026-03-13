"""Background worker for scan execution."""

from collections.abc import Callable
from typing import Optional

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.models.scan import Scan, ScanStatus
from app.services.scan_service import ScanService

logger = get_logger(__name__)


class ScanWorker:
    """Background worker for executing scans."""

    def __init__(self):
        self._running = False
        self._current_scan_id: Optional[int] = None

    async def start(
        self,
        scan_id: int,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> None:
        """
        Start a scan in the background.

        Args:
            scan_id: ID of the scan to execute
            progress_callback: Optional callback for progress updates
        """
        self._current_scan_id = scan_id
        self._running = True

        # Get database session
        session_factory = get_session_factory()
        async with session_factory() as db:
            try:
                # Get scan from database
                result = await db.execute(
                    select(Scan).where(Scan.id == scan_id)
                )
                scan = result.scalar_one_or_none()

                if not scan:
                    logger.error("Scan not found", scan_id=scan_id)
                    return

                if scan.status != ScanStatus.PENDING:
                    logger.warning(
                        "Scan is not in pending state",
                        scan_id=scan_id,
                        status=scan.status,
                    )
                    return

                logger.info("Starting scan worker", scan_id=scan_id)

                # Execute scan
                scan_service = ScanService(db=db)
                await scan_service.execute_scan(scan, progress_callback)

                logger.info("Scan worker completed", scan_id=scan_id)

            except Exception as e:
                logger.exception("Scan worker failed", scan_id=scan_id, error=str(e))

                # Update scan status on error
                result = await db.execute(
                    select(Scan).where(Scan.id == scan_id)
                )
                scan = result.scalar_one_or_none()
                if scan:
                    scan.status = ScanStatus.FAILED
                    scan.error_message = str(e)
                    await db.commit()

            finally:
                self._running = False
                self._current_scan_id = None

    async def cancel(self, scan_id: int) -> bool:
        """
        Cancel a running scan.

        Args:
            scan_id: ID of the scan to cancel

        Returns:
            True if cancelled, False otherwise
        """
        if self._current_scan_id != scan_id:
            return False

        self._running = False

        session_factory = get_session_factory()
        async with session_factory() as db:
            result = await db.execute(
                select(Scan).where(Scan.id == scan_id)
            )
            scan = result.scalar_one_or_none()

            if scan and scan.status == ScanStatus.PROCESSING:
                scan.status = ScanStatus.CANCELLED
                scan.error_message = "Scan cancelled by user"
                await db.commit()

                logger.info("Scan cancelled", scan_id=scan_id)
                return True

        return False

    @property
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._running

    @property
    def current_scan_id(self) -> Optional[int]:
        """Get current scan ID."""
        return self._current_scan_id


# Global worker pool (in production, use Celery or similar)
_worker_pool: dict[int, ScanWorker] = {}


async def execute_scan_background(scan_id: int) -> None:
    """
    Execute a scan in the background.

    This is a convenience function for starting scans without
    managing the worker directly.
    """
    worker = ScanWorker()
    _worker_pool[scan_id] = worker

    try:
        await worker.start(scan_id)
    finally:
        _worker_pool.pop(scan_id, None)


async def cancel_scan_background(scan_id: int) -> bool:
    """Cancel a background scan."""
    worker = _worker_pool.get(scan_id)
    if worker:
        return await worker.cancel(scan_id)
    return False


def get_scan_status(scan_id: int) -> Optional[str]:
    """Get status of a background scan."""
    worker = _worker_pool.get(scan_id)
    if worker:
        return "running" if worker.is_running else "stopped"
    return None
