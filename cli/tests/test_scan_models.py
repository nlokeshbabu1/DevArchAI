"""Tests for scan API helpers and models."""

from __future__ import annotations

from devsec.models.scan import ScanResultsResponse


def test_count_at_or_above_high():
    results = ScanResultsResponse(
        scan_id="abc",
        status="completed",
        severity_counts={"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 0},
    )
    assert results.count_at_or_above("high") == 3
    assert results.count_at_or_above("critical") == 1
    assert results.count_at_or_above("medium") == 6
    assert results.count_at_or_above("none") == 0


def test_scan_status_terminal():
    from devsec.models.scan import ScanStatusResponse

    assert ScanStatusResponse(scan_id="x", status="completed").is_terminal is True
    assert ScanStatusResponse(scan_id="x", status="running").is_terminal is False
