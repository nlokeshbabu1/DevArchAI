"""Unit tests for scan lifecycle helpers."""

from app.models.scan import ScanStage
from app.services.scan_lifecycle import (
    ScanLifecycleStage,
    lifecycle_progress,
    lifecycle_stage_for_internal,
    lifecycle_stages_payload,
)


def test_lifecycle_stages_payload_order():
    stages = lifecycle_stages_payload()
    ids = [s["id"] for s in stages]
    assert ids[0] == "queued"
    assert "connecting_repository" in ids
    assert "scanning" in ids
    assert ids[-1] == "scan_completed"


def test_internal_stage_maps_to_lifecycle():
    assert lifecycle_stage_for_internal(ScanStage.CONNECTING) == ScanLifecycleStage.CONNECTING_REPOSITORY
    assert lifecycle_stage_for_internal(ScanStage.SCANNING) == ScanLifecycleStage.SCANNING
    assert lifecycle_stage_for_internal(ScanStage.NORMALIZATION) == ScanLifecycleStage.ANALYZING


def test_lifecycle_progress_clone_returns_none():
    assert lifecycle_progress(ScanLifecycleStage.CLONING) is None


def test_lifecycle_progress_scanning_uses_scanner_subprogress():
    scanning = lifecycle_progress(
        ScanLifecycleStage.SCANNING,
        scanners_completed=2,
        scanners_total=4,
    )
    assert scanning is not None
    assert 0 < scanning < 100
