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


def test_transition_stage_call_signature_is_consistent():
    """All _transition_stage call sites must match the 3-arg signature.

    Regression guard: a stray positional int (e.g. _transition_stage(scan, stage, 88, msg))
    raised "SyncScanService._transition_stage() takes 4 positional arguments but 5 were given"
    and failed scans at the ANALYZING_FINDINGS stage.
    """
    import ast
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "app" / "workers" / "tasks" / "scan_repository.py"
    tree = ast.parse(path.read_text())

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = getattr(fn, "attr", None) if isinstance(fn, ast.Attribute) else None
        if name != "_transition_stage":
            continue
        if node.args:
            for arg in node.args[1:]:  # skip the positional (self) receiver
                if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                    raise AssertionError(
                        f"_transition_stage called with stray positional int at line {node.lineno}: "
                        f"{ast.unparse(node)}"
                    )
