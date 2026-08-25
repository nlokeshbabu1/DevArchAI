"""Tests for lifecycle progress rendering."""

from __future__ import annotations

from devsec.models.scan import ScanStateResponse, TechnologyResult
from devsec.output.progress_display import LifecycleProgressRenderer, format_technology_label


def test_format_technology_label():
    assert format_technology_label("github_actions") == "GitHub Actions"
    assert format_technology_label("custom", "My Stack") == "My Stack"


def test_renderer_marks_completed_stages():
    renderer = LifecycleProgressRenderer()
    state = ScanStateResponse(
        scan_id="abc",
        status="running",
        stage="scanning",
        progress=50,
        is_terminal=False,
    )
    renderer.apply_state(state)
    assert "connecting_repository" in renderer.completed_stages
    assert renderer.current_stage == "scanning"


def test_renderer_tracks_technology_completion():
    renderer = LifecycleProgressRenderer()
    renderer.apply_ws(
        "technology_detected",
        {"technology": "docker", "name": "Docker"},
    )
    renderer.apply_ws("technology_scan_completed", {"technology": "docker", "findings": 4})
    assert renderer.technologies["docker"].findings == 4
    assert renderer.tech_status["docker"] == "completed"


def test_renderer_ai_status():
    renderer = LifecycleProgressRenderer()
    renderer.apply_ws("ai_started", {})
    assert renderer.ai_status == "processing"
    renderer.apply_ws("ai.analysis.completed", {})
    assert renderer.ai_status == "completed"
