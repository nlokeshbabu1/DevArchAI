"""
Scan timeout detection service.

Periodically checks for scans stuck in RUNNING/PROCESSING state
and marks them as FAILED after a configurable timeout.
"""

import asyncio
from datetime import datetime, timedelta

import structlog
from sqlalchemy import select

from app.models.scan import Scan, ScanStatus

logger = structlog.get_logger(__name__)

# Default timeout: 10 minutes for a scan
SCAN_TIMEOUT_MINUTES = 10
CHECK_INTERVAL_SECONDS = 60  # Check every 60 seconds


async def detect_stuck_scans():
    """
    Background task that detects scans stuck in RUNNING/PROCESSING state.

    If a scan has been in PROCESSING state for longer than SCAN_TIMEOUT_MINUTES,
    it is marked as FAILED with a timeout error message.
    """
    from app.db.session import get_session_factory

    while True:
        try:
            async with get_session_factory()() as db:
                cutoff = datetime.utcnow() - timedelta(minutes=SCAN_TIMEOUT_MINUTES)

                # Find scans stuck in PROCESSING state beyond timeout
                result = await db.execute(
                    select(Scan).where(
                        Scan.status.in_([ScanStatus.PROCESSING, ScanStatus.QUEUED]),
                        Scan.started_at < cutoff,
                        Scan.started_at.isnot(None),
                    )
                )
                stuck_scans = result.scalars().all()

                for scan in stuck_scans:
                    logger.warning(
                        f"[TIMEOUT] scan={scan.id} status={scan.status.value} "
                        f"started_at={scan.started_at} timeout_minutes={SCAN_TIMEOUT_MINUTES}"
                    )

                    # Mark as failed
                    scan.status = ScanStatus.FAILED
                    scan.error_message = f"Scan timed out after {SCAN_TIMEOUT_MINUTES} minutes"
                    scan.completed_at = datetime.utcnow()
                    scan.current_stage = None

                    # Broadcast failure via WebSocket
                    try:
                        from app.websockets.scan_progress import scan_progress_manager
                        await scan_progress_manager.broadcast_progress(
                            scan_id=str(scan.id),
                            progress=0,
                            status="failed",
                            current_step="Scan timed out",
                            error_message=f"Scan timed out after {SCAN_TIMEOUT_MINUTES} minutes",
                        )
                    except Exception as ws_error:
                        logger.warning(f"Failed to broadcast timeout for scan {scan.id}: {ws_error}")

                    # Clean up progress store
                    try:
                        from app.services.scan_progress_store import get_scan_progress_store
                        store = get_scan_progress_store()
                        await store.fail_scan(str(scan.id), f"Scan timed out after {SCAN_TIMEOUT_MINUTES} minutes")
                    except Exception as store_error:
                        logger.warning(f"Failed to update progress store for timed-out scan {scan.id}: {store_error}")

                await db.commit()

                if stuck_scans:
                    logger.info(f"[TIMEOUT] Marked {len(stuck_scans)} stuck scans as failed")

        except Exception as e:
            logger.error(f"[TIMEOUT] Error in stuck scan detection: {e}")

        # Wait before next check
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


async def start_timeout_detector():
    """Start the timeout detection background task."""
    logger.info(f"[TIMEOUT] Starting scan timeout detector (timeout={SCAN_TIMEOUT_MINUTES}min, interval={CHECK_INTERVAL_SECONDS}s)")
    asyncio.create_task(detect_stuck_scans())
