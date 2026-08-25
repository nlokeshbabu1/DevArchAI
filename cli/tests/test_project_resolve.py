"""Tests for project ID resolution (UUID, prefix, auto-select)."""

from __future__ import annotations

import httpx
import pytest

from devsec.api.client import ApiClient
from devsec.api.projects import resolve_project, resolve_project_for_command
from devsec.config import Config

FULL_ID = "ae8f8620-1234-5678-9abc-def012345678"
PROJECT = {
    "id": FULL_ID,
    "name": "nlokeshbabu1/ECOMMERCE",
    "url": "https://github.com/nlokeshbabu1/ECOMMERCE",
    "default_branch": "main",
    "is_private": False,
    "is_active": True,
    "created_at": "2026-08-10T16:47:00Z",
}


@pytest.fixture
def client(tmp_path):
    cfg = Config(
        config_file=tmp_path / "config.toml",
        env={"DEVSEC_API_URL": "http://127.0.0.1:8000", "DEVSEC_API_TOKEN": "sk-test"},
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url.path).endswith("/repositories"):
            return httpx.Response(
                200,
                json={"repositories": [PROJECT], "total": 1, "page": 1, "page_size": 100},
            )
        if str(request.url.path).endswith(f"/repositories/{FULL_ID}"):
            return httpx.Response(200, json=PROJECT)
        return httpx.Response(404, json={"detail": "not found"})

    api = ApiClient(cfg, transport=httpx.MockTransport(handler))
    yield api
    api.close()


def test_resolve_project_by_prefix(client):
    project = resolve_project(client, "ae8f8620")
    assert project.id == FULL_ID


def test_resolve_project_auto_single(client):
    project = resolve_project(client, None, auto_single=True)
    assert project.id == FULL_ID


def test_resolve_project_for_command_uses_selected(client):
    project = resolve_project_for_command(client, None, selected_project="ae8f8620")
    assert project.id == FULL_ID
