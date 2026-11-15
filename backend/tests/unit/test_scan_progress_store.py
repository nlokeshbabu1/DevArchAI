"""Tests for app.services.scan_progress_store — pure in-memory scan progress tracking."""

import pytest
from datetime import datetime, timedelta

from app.services.scan_progress_store import ScanProgressStore, get_scan_progress_store
from app.services.scan_progress_steps import progress_store_step_labels
from app.schemas.scan_progress import StepStatus


@pytest.fixture
def store():
    """Fresh ScanProgressStore for each test."""
    return ScanProgressStore()


AUTHORITATIVE_STEP_NAMES = progress_store_step_labels()


# ---------------------------------------------------------------------------
# create_scan
# ---------------------------------------------------------------------------
class TestCreateScan:
    @pytest.mark.asyncio
    async def test_creates_scan_with_defaults(self, store):
        progress = await store.create_scan("s1")
        assert progress.scan_id == "s1"
        assert progress.status == "pending"
        assert progress.progress == 0
        assert progress.detected_stack == []
        assert progress.logs == ["Initializing scan..."]
        assert progress.created_at is not None

    @pytest.mark.asyncio
    async def test_default_steps_are_pending(self, store):
        progress = await store.create_scan("s2")
        assert len(progress.steps) == 5
        for step in progress.steps:
            assert step.status == StepStatus.PENDING
            assert step.progress == 0

    @pytest.mark.asyncio
    async def test_step_names(self, store):
        progress = await store.create_scan("s3")
        names = [s.name for s in progress.steps]
        assert names == AUTHORITATIVE_STEP_NAMES


# ---------------------------------------------------------------------------
# get_progress
# ---------------------------------------------------------------------------
class TestGetProgress:
    @pytest.mark.asyncio
    async def test_returns_existing_scan(self, store):
        created = await store.create_scan("s1")
        got = await store.get_progress("s1")
        assert got is not None
        assert got.scan_id == created.scan_id

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown(self, store):
        assert await store.get_progress("nonexistent") is None


# ---------------------------------------------------------------------------
# update_status
# ---------------------------------------------------------------------------
class TestUpdateStatus:
    @pytest.mark.asyncio
    async def test_updates_status_and_progress(self, store):
        await store.create_scan("s1")
        await store.update_status("s1", "running", 30, current_step="Clone repository")
        p = await store.get_progress("s1")
        assert p.status == "running"
        assert p.progress == 30
        assert p.current_step == "Clone repository"

    @pytest.mark.asyncio
    async def test_progress_is_monotonic_while_running(self, store):
        await store.create_scan("s1")
        await store.update_status("s1", "running", 40)
        await store.update_status("s1", "running", 25)
        p = await store.get_progress("s1")
        assert p.progress == 40

    @pytest.mark.asyncio
    async def test_does_not_regress_from_completed_to_running(self, store):
        await store.create_scan("s1")
        await store.complete_scan("s1")
        await store.update_status("s1", "running", 50)
        p = await store.get_progress("s1")
        assert p.status == "completed"
        assert p.progress == 100

    @pytest.mark.asyncio
    async def test_normalizes_lifecycle_id_as_current_step(self, store):
        await store.create_scan("s1")
        await store.update_status("s1", "running", 10, current_step="connecting_repository")
        p = await store.get_progress("s1")
        assert p.current_step == "Connect to repository"

    @pytest.mark.asyncio
    async def test_noop_for_unknown_scan(self, store):
        await store.update_status("ghost", "running", 50)
        assert await store.get_progress("ghost") is None


# ---------------------------------------------------------------------------
# update_step
# ---------------------------------------------------------------------------
class TestUpdateStep:
    @pytest.mark.asyncio
    async def test_updates_step_status_and_progress(self, store):
        await store.create_scan("s1")
        await store.update_step("s1", "Connect to repository", StepStatus.RUNNING, progress=10)
        p = await store.get_progress("s1")
        step = p.steps[0]
        assert step.status == StepStatus.RUNNING
        assert step.progress == 10
        assert step.started_at is not None

    @pytest.mark.asyncio
    async def test_accepts_lifecycle_stage_id(self, store):
        await store.create_scan("s1")
        await store.update_step("s1", "connecting_repository", StepStatus.RUNNING, progress=5)
        step = (await store.get_progress("s1")).steps[0]
        assert step.status == StepStatus.RUNNING

    @pytest.mark.asyncio
    async def test_maps_cloned_to_clone_step(self, store):
        await store.create_scan("s1")
        await store.update_step("s1", "cloned", StepStatus.COMPLETED, progress=100)
        step = (await store.get_progress("s1")).steps[1]
        assert step.name == "Clone repository"
        assert step.status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_sets_completed_at_on_complete(self, store):
        await store.create_scan("s1")
        await store.update_step("s1", "Connect to repository", StepStatus.COMPLETED, progress=100)
        step = (await store.get_progress("s1")).steps[0]
        assert step.status == StepStatus.COMPLETED
        assert step.completed_at is not None

    @pytest.mark.asyncio
    async def test_sets_error_on_failed(self, store):
        await store.create_scan("s1")
        await store.update_step("s1", "Clone repository", StepStatus.FAILED, error="timeout")
        step = (await store.get_progress("s1")).steps[1]
        assert step.status == StepStatus.FAILED
        assert step.error == "timeout"
        assert step.completed_at is not None

    @pytest.mark.asyncio
    async def test_unknown_step_is_noop(self, store):
        await store.create_scan("s1")
        await store.update_step("s1", "not-a-real-step", StepStatus.RUNNING)
        for step in (await store.get_progress("s1")).steps:
            assert step.status == StepStatus.PENDING

    @pytest.mark.asyncio
    async def test_noop_for_unknown_scan(self, store):
        await store.update_step("ghost", "step", StepStatus.RUNNING)
        assert await store.get_progress("ghost") is None


# ---------------------------------------------------------------------------
# Progress isolation
# ---------------------------------------------------------------------------
class TestProgressIsolation:
    @pytest.mark.asyncio
    async def test_concurrent_scans_do_not_leak(self, store):
        await store.create_scan("scan-a")
        await store.create_scan("scan-b")
        await store.update_step("scan-a", "Security scan", StepStatus.RUNNING, progress=55)
        await store.update_status("scan-b", "running", 12, current_step="Clone repository")
        a = await store.get_progress("scan-a")
        b = await store.get_progress("scan-b")
        assert a.steps[3].status == StepStatus.RUNNING
        assert b.steps[3].status == StepStatus.PENDING
        assert b.progress == 12


# ---------------------------------------------------------------------------
# add_log
# ---------------------------------------------------------------------------
class TestAddLog:
    @pytest.mark.asyncio
    async def test_appends_timestamped_log(self, store):
        await store.create_scan("s1")
        await store.add_log("s1", "hello")
        logs = (await store.get_progress("s1")).logs
        assert len(logs) == 2  # init log + new log
        assert logs[0] == "Initializing scan..."
        assert logs[1].endswith("hello")

    @pytest.mark.asyncio
    async def test_truncates_at_50(self, store):
        await store.create_scan("s1")
        for i in range(55):
            await store.add_log("s1", f"msg-{i}")
        logs = (await store.get_progress("s1")).logs
        assert len(logs) == 50
        assert logs[-1].endswith("msg-54")
        assert logs[0].endswith("msg-5")

    @pytest.mark.asyncio
    async def test_noop_for_unknown_scan(self, store):
        await store.add_log("ghost", "msg")
        assert await store.get_progress("ghost") is None


# ---------------------------------------------------------------------------
# update_detected_stack
# ---------------------------------------------------------------------------
class TestUpdateDetectedStack:
    @pytest.mark.asyncio
    async def test_sets_stack(self, store):
        await store.create_scan("s1")
        await store.update_detected_stack("s1", ["python", "docker"])
        p = await store.get_progress("s1")
        assert p.detected_stack == ["python", "docker"]

    @pytest.mark.asyncio
    async def test_noop_for_unknown_scan(self, store):
        await store.update_detected_stack("ghost", ["x"])
        assert await store.get_progress("ghost") is None


# ---------------------------------------------------------------------------
# update_stage
# ---------------------------------------------------------------------------
class TestUpdateStage:
    @pytest.mark.asyncio
    async def test_sets_stage_and_counts(self, store):
        await store.create_scan("s1")
        await store.update_stage("s1", "scanning", files_scanned=10, total_files=20)
        p = await store.get_progress("s1")
        assert p.stage == "scanning"
        assert p.files_scanned == 10
        assert p.total_files == 20

    @pytest.mark.asyncio
    async def test_noop_for_unknown_scan(self, store):
        await store.update_stage("ghost", "stage")
        assert await store.get_progress("ghost") is None


# ---------------------------------------------------------------------------
# update_files_list
# ---------------------------------------------------------------------------
class TestUpdateFilesList:
    @pytest.mark.asyncio
    async def test_sets_files_list(self, store):
        await store.create_scan("s1")
        await store.update_files_list("s1", ["a.py", "b.py"])
        p = await store.get_progress("s1")
        assert p.files_list == ["a.py", "b.py"]

    @pytest.mark.asyncio
    async def test_noop_for_unknown_scan(self, store):
        await store.update_files_list("ghost", ["x"])
        assert await store.get_progress("ghost") is None


# ---------------------------------------------------------------------------
# complete_scan
# ---------------------------------------------------------------------------
class TestCompleteScan:
    @pytest.mark.asyncio
    async def test_marks_all_pending_steps_completed(self, store):
        await store.create_scan("s1")
        await store.complete_scan("s1")
        p = await store.get_progress("s1")
        assert p.status == "completed"
        assert p.progress == 100
        assert p.completed_at is not None
        for step in p.steps:
            assert step.status == StepStatus.COMPLETED
            assert step.progress == 100
            assert step.completed_at is not None

    @pytest.mark.asyncio
    async def test_completes_running_step(self, store):
        await store.create_scan("s1")
        await store.update_step("s1", "Connect to repository", StepStatus.RUNNING)
        await store.complete_scan("s1")
        p = await store.get_progress("s1")
        assert p.steps[0].status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_noop_for_unknown_scan(self, store):
        await store.complete_scan("ghost")
        assert await store.get_progress("ghost") is None


# ---------------------------------------------------------------------------
# fail_scan
# ---------------------------------------------------------------------------
class TestFailScan:
    @pytest.mark.asyncio
    async def test_fails_running_step(self, store):
        await store.create_scan("s1")
        await store.update_step("s1", "Clone repository", StepStatus.RUNNING)
        await store.fail_scan("s1", "network error")
        p = await store.get_progress("s1")
        assert p.status == "failed"
        assert p.error_message == "network error"
        step = p.steps[1]
        assert step.status == StepStatus.FAILED
        assert step.error == "network error"
        assert step.completed_at is not None

    @pytest.mark.asyncio
    async def test_noop_for_unknown_scan(self, store):
        await store.fail_scan("ghost", "err")
        assert await store.get_progress("ghost") is None


# ---------------------------------------------------------------------------
# cleanup_old_scans
# ---------------------------------------------------------------------------
class TestCleanupOldScans:
    @pytest.mark.asyncio
    async def test_removes_old_completed_scans(self, store):
        await store.create_scan("s1")
        await store.create_scan("s2")
        await store.complete_scan("s1")
        await store.complete_scan("s2")
        # Manually backdate completed_at for s1
        p1 = await store.get_progress("s1")
        p1.completed_at = datetime.utcnow() - timedelta(hours=25)

        await store.cleanup_old_scans(max_age_hours=24)
        assert await store.get_progress("s1") is None
        assert await store.get_progress("s2") is not None

    @pytest.mark.asyncio
    async def test_keeps_non_completed_scans(self, store):
        await store.create_scan("s1")
        await store.cleanup_old_scans()
        assert await store.get_progress("s1") is not None

    @pytest.mark.asyncio
    async def test_keeps_recent_completed_scans(self, store):
        await store.create_scan("s1")
        await store.complete_scan("s1")
        await store.cleanup_old_scans(max_age_hours=24)
        assert await store.get_progress("s1") is not None


# ---------------------------------------------------------------------------
# get_scan_progress_store singleton
# ---------------------------------------------------------------------------
class TestGetScanProgressStoreSingleton:
    def test_returns_same_instance(self):
        a = get_scan_progress_store()
        b = get_scan_progress_store()
        assert a is b

    def test_is_scan_progress_store(self):
        assert isinstance(get_scan_progress_store(), ScanProgressStore)
