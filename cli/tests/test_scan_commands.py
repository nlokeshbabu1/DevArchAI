"""Scan command integration tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from typer.testing import CliRunner

from devsec.config import SecretStore
from devsec.main import app

runner = CliRunner()

PROJECT = {
    "id": "11111111-2222-3333-4444-555555555555",
    "name": "acme/infra",
    "url": "https://github.com/acme/infra",
    "default_branch": "main",
    "is_private": False,
    "is_active": True,
    "created_at": "2026-01-15T08:30:00Z",
}

SCAN_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.fixture
def isolated_env(tmp_path: Path):
    old = {k: os.environ.get(k) for k in ("XDG_CONFIG_HOME", "DEVSEC_API_URL", "DEVSEC_API_KEY")}
    os.environ["XDG_CONFIG_HOME"] = str(tmp_path)
    os.environ["DEVSEC_API_URL"] = "http://127.0.0.1:59999"
    os.environ.pop("DEVSEC_API_KEY", None)
    store = SecretStore(config_file=tmp_path / "devsec" / "config.toml")
    store.set_token("sk-scan-test")
    cfg = tmp_path / "devsec" / "config.toml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text('selected_project = "11111111-2222-3333-4444-555555555555"\n', encoding="utf-8")
    yield tmp_path
    for key, value in old.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _mock_http(handler):
    original_client = httpx.Client

    def client_factory(**kwargs: object) -> httpx.Client:
        kwargs.pop("transport", None)
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    return patch("devsec.api.client.httpx.Client", client_factory)


def test_scan_requires_project(isolated_env):
    cfg = isolated_env / "devsec" / "config.toml"
    cfg.write_text("", encoding="utf-8")
    result = runner.invoke(app, ["scan", "--json"])
    assert result.exit_code == 2
    assert "No project selected" in result.stderr or "No project selected" in result.stdout


def test_scan_start_no_wait(isolated_env):
    def handler(request: httpx.Request) -> httpx.Response:
        path = str(request.url.path)
        if path.endswith("/repositories/11111111-2222-3333-4444-555555555555"):
            return httpx.Response(200, json=PROJECT)
        if path.endswith("/scan/start"):
            return httpx.Response(
                200,
                json={
                    "scan_id": SCAN_ID,
                    "status": "pending",
                    "repository_id": PROJECT["id"],
                    "repository_url": PROJECT["url"],
                    "branch": "main",
                },
            )
        return httpx.Response(404, json={"detail": "not found"})

    with _mock_http(handler):
        result = runner.invoke(app, ["scan", "--no-wait", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["scan_id"] == SCAN_ID


def test_scan_status(isolated_env):
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url.path).endswith(f"/scan/status/{SCAN_ID}"):
            return httpx.Response(
                200,
                json={
                    "scan_id": SCAN_ID,
                    "status": "running",
                    "progress": 42,
                    "current_step": "Scanning Terraform",
                },
            )
        return httpx.Response(404, json={"detail": "not found"})

    with _mock_http(handler):
        result = runner.invoke(app, ["scan", "status", SCAN_ID, "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["progress"] == 42


def test_scan_results_policy_failure(isolated_env):
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url.path).endswith(f"/scan/results/{SCAN_ID}"):
            return httpx.Response(
                200,
                json={
                    "scan_id": SCAN_ID,
                    "status": "completed",
                    "findings_count": 2,
                    "severity_counts": {"HIGH": 2},
                    "findings": [
                        {"severity": "HIGH", "rule_name": "S3 public bucket"},
                        {"severity": "HIGH", "rule_name": "Open SG"},
                    ],
                },
            )
        return httpx.Response(404, json={"detail": "not found"})

    with _mock_http(handler):
        result = runner.invoke(app, ["scan", "results", SCAN_ID, "--json"])
    assert result.exit_code == 1, result.output
    data = json.loads(result.stdout)
    assert data["passed"] is False


def test_scan_full_workflow_polling(isolated_env):
    status_calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        path = str(request.url.path)
        if path.endswith("/repositories/11111111-2222-3333-4444-555555555555"):
            return httpx.Response(200, json=PROJECT)
        if path.endswith("/scan/start"):
            return httpx.Response(
                200,
                json={"scan_id": SCAN_ID, "status": "pending", "repository_url": PROJECT["url"]},
            )
        if path.endswith(f"/scan/status/{SCAN_ID}"):
            status_calls["count"] += 1
            status = "completed" if status_calls["count"] >= 2 else "running"
            progress = 100 if status == "completed" else 50
            return httpx.Response(
                200,
                json={
                    "scan_id": SCAN_ID,
                    "status": status,
                    "progress": progress,
                    "current_step": "done" if status == "completed" else "working",
                },
            )
        if path.endswith(f"/scan/results/{SCAN_ID}"):
            return httpx.Response(
                200,
                json={
                    "scan_id": SCAN_ID,
                    "status": "completed",
                    "findings_count": 0,
                    "severity_counts": {},
                    "findings": [],
                    "overall_score": 95,
                },
            )
        return httpx.Response(404, json={"detail": "not found"})

    with _mock_http(handler):
        result = runner.invoke(app, ["scan", "--json", "--quiet"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["passed"] is True
    assert data["results"]["overall_score"] == 95
