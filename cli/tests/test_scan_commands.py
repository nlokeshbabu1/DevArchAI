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

STATE_COMPLETED = {
    "scan_id": SCAN_ID,
    "status": "completed",
    "stage": "scan_completed",
    "progress": 100,
    "is_terminal": True,
    "message": "Scan completed",
    "technologies": [
        {"id": "terraform", "name": "Terraform", "status": "completed", "findings": 2},
    ],
    "severity_counts": {"high": 0, "medium": 0, "low": 0, "critical": 0, "info": 0},
    "findings_count": 0,
    "ai_status": "completed",
}


def _state_response(status: str, *, progress: int = 50) -> dict:
    return {
        "scan_id": SCAN_ID,
        "status": status,
        "stage": "scanning" if status != "completed" else "scan_completed",
        "progress": progress,
        "is_terminal": status in {"completed", "failed", "cancelled"},
        "message": status,
        "technologies": [],
        "severity_counts": {},
        "findings_count": 0,
    }


@pytest.fixture
def isolated_env(tmp_path: Path):
    old = {k: os.environ.get(k) for k in ("XDG_CONFIG_HOME", "DEVSEC_API_URL", "DEVSEC_API_KEY")}
    os.environ["XDG_CONFIG_HOME"] = str(tmp_path)
    os.environ["DEVSEC_API_URL"] = "http://127.0.0.1:59999"
    os.environ["DEVSEC_DISABLE_WEBSOCKET"] = "1"
    os.environ.pop("DEVSEC_API_KEY", None)
    os.environ.pop("DEVSEC_DISABLE_WEBSOCKET", None)
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


def test_scan_requires_git_or_project(isolated_env):
    cfg = isolated_env / "devsec" / "config.toml"
    cfg.write_text("", encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url.path).endswith("/repositories"):
            return httpx.Response(
                200,
                json={"repositories": [], "total": 0, "page": 1, "page_size": 100},
            )
        return httpx.Response(404, json={"detail": "not found"})

    with _mock_http(handler):
        result = runner.invoke(app, ["scan", "--json", "--path", str(isolated_env)])
    assert result.exit_code == 2
    body = result.stdout
    assert "Not a git repository" in body or "No Git remote" in body or "No project selected" in body


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
        if path.endswith(f"/scan/state/{SCAN_ID}"):
            status_calls["count"] += 1
            status = "completed" if status_calls["count"] >= 2 else "running"
            return httpx.Response(
                200,
                json=_state_response(status, progress=100 if status == "completed" else 50),
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


def test_scan_with_repo_flag(isolated_env):
    def handler(request: httpx.Request) -> httpx.Response:
        path = str(request.url.path)
        if path.endswith("/repositories") and request.method == "GET":
            return httpx.Response(
                200,
                json={"repositories": [], "total": 0, "page": 1, "page_size": 100},
            )
        if path.endswith("/repositories") and request.method == "POST":
            return httpx.Response(201, json=PROJECT)
        if path.endswith("/scan/start"):
            return httpx.Response(
                200,
                json={"scan_id": SCAN_ID, "status": "pending", "repository_url": PROJECT["url"]},
            )
        if path.endswith(f"/scan/state/{SCAN_ID}"):
            return httpx.Response(200, json=STATE_COMPLETED)
        if path.endswith(f"/scan/results/{SCAN_ID}"):
            return httpx.Response(
                200,
                json={
                    "scan_id": SCAN_ID,
                    "status": "completed",
                    "findings_count": 0,
                    "severity_counts": {},
                    "findings": [],
                },
            )
        return httpx.Response(404, json={"detail": "not found"})

    with _mock_http(handler):
        result = runner.invoke(
            app,
            ["scan", "--repo", "https://github.com/acme/infra", "--json", "--quiet"],
        )
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["scan_id"] == SCAN_ID


def test_scan_requires_branch_when_no_default(isolated_env):
    project_no_branch = {**PROJECT, "default_branch": ""}

    def handler(request: httpx.Request) -> httpx.Response:
        path = str(request.url.path)
        if path.endswith("/repositories/11111111-2222-3333-4444-555555555555"):
            return httpx.Response(200, json=project_no_branch)
        return httpx.Response(404, json={"detail": "not found"})

    with _mock_http(handler):
        result = runner.invoke(app, ["scan", "--no-wait", "--json"])
    assert result.exit_code == 2
    assert "Branch not specified" in result.stdout or "Branch not specified" in result.output


def test_project_set_branch(isolated_env):
    def handler(request: httpx.Request) -> httpx.Response:
        path = str(request.url.path)
        if path.endswith("/repositories/11111111-2222-3333-4444-555555555555") and request.method == "PUT":
            body = json.loads(request.content.decode())
            assert body["default_branch"] == "master"
            return httpx.Response(200, json={**PROJECT, "default_branch": "master"})
        if path.endswith("/repositories/11111111-2222-3333-4444-555555555555"):
            return httpx.Response(200, json=PROJECT)
        return httpx.Response(404, json={"detail": "not found"})

    with _mock_http(handler):
        result = runner.invoke(
            app,
            ["project", "set-branch", "11111111-2222-3333-4444-555555555555", "master", "--json"],
        )
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["default_branch"] == "master"
