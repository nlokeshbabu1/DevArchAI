"""
In-memory scan progress store.

Stores real-time scan progress for polling by frontend.
"""

import asyncio
from datetime import datetime

import structlog

from app.schemas.scan_progress import ScanProgressResponse, ScanStep, StepStatus

logger = structlog.get_logger(__name__)


class ScanProgressStore:
    """In-memory store for scan progress tracking."""

    def __init__(self):
        self._store: dict[str, ScanProgressResponse] = {}
        self._lock = asyncio.Lock()

    async def create_scan(self, scan_id: str) -> ScanProgressResponse:
        """Create a new scan progress entry."""
        async with self._lock:
            progress = ScanProgressResponse(
                scan_id=scan_id,
                status="pending",
                progress=0,
                steps=self._get_default_steps(),
                detected_stack=[],
                logs=["Initializing scan..."],
                created_at=datetime.utcnow(),
            )
            self._store[scan_id] = progress
            logger.info(f"Scan progress created: {scan_id}")
            return progress

    async def update_status(self, scan_id: str, status: str, progress: int, current_step: str | None = None):
        """Update scan status and progress."""
        async with self._lock:
            if scan_id not in self._store:
                logger.warning(f"[LIFECYCLE] scan={scan_id} event=UPDATE_SKIP reason=not_in_store")
                return

            progress_obj = self._store[scan_id]
            # Track previous progress for staleness detection
            progress_obj._last_progress = progress_obj.progress
            progress_obj.status = status
            progress_obj.progress = progress
            if current_step:
                progress_obj.current_step = current_step

            logger.debug(
                f"[LIFECYCLE] scan={scan_id} event=STORE_UPDATE "
                f"status={status} progress={progress} step={current_step} "
                f"timestamp={datetime.utcnow().isoformat()}"
            )

    async def update_step(self, scan_id: str, step_name: str, status: StepStatus, progress: int = 0, error: str | None = None):
        """Update individual step status."""
        async with self._lock:
            if scan_id not in self._store:
                return

            progress_obj = self._store[scan_id]
            for step in progress_obj.steps:
                if step.name == step_name:
                    step.status = status
                    step.progress = progress
                    if error:
                        step.error = error
                    if status == StepStatus.RUNNING:
                        step.started_at = datetime.utcnow()
                    elif status in [StepStatus.COMPLETED, StepStatus.FAILED]:
                        step.completed_at = datetime.utcnow()
                    break

    async def add_log(self, scan_id: str, message: str):
        """Add a log message."""
        async with self._lock:
            if scan_id not in self._store:
                return

            progress_obj = self._store[scan_id]
            timestamp = datetime.utcnow().strftime("%H:%M:%S")
            progress_obj.logs.append(f"[{timestamp}] {message}")

            # Keep only last 50 logs
            if len(progress_obj.logs) > 50:
                progress_obj.logs = progress_obj.logs[-50:]

    async def update_detected_stack(self, scan_id: str, stack: list[str]):
        """Update detected technology stack."""
        async with self._lock:
            if scan_id not in self._store:
                return

            progress_obj = self._store[scan_id]
            progress_obj.detected_stack = stack

    async def update_stage(self, scan_id: str, stage: str, files_scanned: int = 0, total_files: int = 0):
        """Update scan stage and file counts."""
        async with self._lock:
            if scan_id not in self._store:
                return

            progress_obj = self._store[scan_id]
            progress_obj.stage = stage
            progress_obj.files_scanned = files_scanned
            progress_obj.total_files = total_files

    async def update_files_list(self, scan_id: str, file_paths: list[str]):
        """Update the list of files being scanned."""
        async with self._lock:
            if scan_id not in self._store:
                return

            progress_obj = self._store[scan_id]
            progress_obj.files_list = file_paths

    async def get_progress(self, scan_id: str) -> ScanProgressResponse | None:
        """Get current scan progress."""
        async with self._lock:
            entry = self._store.get(scan_id)
            if entry:
                # Track previous progress for staleness detection
                entry._last_progress = getattr(entry, '_last_progress', entry.progress)
            return entry

    async def _cleanup_scan(self, scan_id: str):
        """Remove a scan entry from the progress store (used when DB has authoritative terminal state)."""
        async with self._lock:
            self._store.pop(scan_id, None)
            logger.info(f"Scan progress entry cleaned up: {scan_id}")

    async def complete_scan(self, scan_id: str):
        """Mark scan as completed."""
        async with self._lock:
            if scan_id not in self._store:
                logger.warning(f"[LIFECYCLE] scan={scan_id} event=COMPLETE_SKIP reason=not_in_store")
                return

            progress_obj = self._store[scan_id]
            progress_obj.status = "completed"
            progress_obj.progress = 100
            progress_obj.completed_at = datetime.utcnow()

            # Mark all steps as completed
            for step in progress_obj.steps:
                if step.status == StepStatus.PENDING:
                    step.status = StepStatus.COMPLETED
                    step.progress = 100
                    step.completed_at = datetime.utcnow()

            logger.info(
                f"[LIFECYCLE] scan={scan_id} event=STORE_COMPLETE "
                f"status=completed progress=100 timestamp={datetime.utcnow().isoformat()}"
            )

    async def fail_scan(self, scan_id: str, error_message: str):
        """Mark scan as failed."""
        async with self._lock:
            if scan_id not in self._store:
                logger.warning(f"[LIFECYCLE] scan={scan_id} event=FAIL_SKIP reason=not_in_store")
                return

            progress_obj = self._store[scan_id]
            progress_obj.status = "failed"
            progress_obj.error_message = error_message

            # Mark current step as failed
            for step in progress_obj.steps:
                if step.status == StepStatus.RUNNING:
                    step.status = StepStatus.FAILED
                    step.error = error_message
                    step.completed_at = datetime.utcnow()
                    break

            logger.info(
                f"[LIFECYCLE] scan={scan_id} event=STORE_FAIL "
                f"status=failed timestamp={datetime.utcnow().isoformat()}"
            )

    async def cleanup_old_scans(self, max_age_hours: int = 24):
        """Remove old scan progress entries."""
        async with self._lock:
            now = datetime.utcnow()
            to_remove = []

            for scan_id, progress in self._store.items():
                if progress.completed_at:
                    age = (now - progress.completed_at).total_seconds() / 3600
                    if age > max_age_hours:
                        to_remove.append(scan_id)

            for scan_id in to_remove:
                del self._store[scan_id]
                logger.debug(f"Cleaned up old scan: {scan_id}")

    def _get_default_steps(self) -> list[ScanStep]:
        """Get default scan steps."""
        return [
            ScanStep(name="Connecting to GitHub", status=StepStatus.PENDING),
            ScanStep(name="Fetching repository", status=StepStatus.PENDING),
            ScanStep(name="Detecting technologies", status=StepStatus.PENDING),
            ScanStep(name="Running security rules", status=StepStatus.PENDING),
            ScanStep(name="Generating AI suggestions", status=StepStatus.PENDING),
            ScanStep(name="Calculating score", status=StepStatus.PENDING),
        ]


# Global instance
scan_progress_store = ScanProgressStore()


def get_scan_progress_store() -> ScanProgressStore:
    """Get the global scan progress store."""
    return scan_progress_store
