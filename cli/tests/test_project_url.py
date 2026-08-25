"""Tests for repository URL resolution and registration."""

from __future__ import annotations

import httpx
import pytest

from devsec.api.client import ApiClient
from devsec.api.projects import find_project_by_url, resolve_or_register_by_url
from devsec.config import Config

PROJECT = {
    "id": "11111111-2222-3333-4444-555555555555",
    "name": "acme/infra",
    "url": "https://github.com/acme/infra.git",
    "default_branch": "main",
    "is_private": False,
    "is_active": True,
    "created_at": "2026-01-15T08:30:00Z",
}


@pytest.fixture
def client(tmp_path):
    cfg = Config(
        config_file=tmp_path / "config.toml",
        env={"DEVSEC_API_URL": "http://127.0.0.1:8000", "DEVSEC_API_KEY": "sk-test"},
    )
    posts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = str(request.url.path)
        if path.endswith("/repositories") and request.method == "GET":
            return httpx.Response(
                200,
                json={"repositories": [PROJECT], "total": 1, "page": 1, "page_size": 100},
            )
        if path.endswith("/repositories") and request.method == "POST":
            posts.append(request.content.decode())
            return httpx.Response(201, json=PROJECT)
        return httpx.Response(404, json={"detail": "not found"})

    api = ApiClient(cfg, transport=httpx.MockTransport(handler))
    api._posts = posts  # type: ignore[attr-defined]
    yield api
    api.close()


def test_find_project_by_url_normalizes_git_suffix(client):
    found = find_project_by_url(client, "https://github.com/acme/infra")
    assert found is not None
    assert found.id == PROJECT["id"]


def test_resolve_or_register_returns_existing(client):
    project = resolve_or_register_by_url(client, "https://github.com/acme/infra")
    assert project.id == PROJECT["id"]
    assert client._posts == []  # type: ignore[attr-defined]


def test_resolve_or_register_creates_when_missing(tmp_path):
    cfg = Config(
        config_file=tmp_path / "config.toml",
        env={"DEVSEC_API_URL": "http://127.0.0.1:8000", "DEVSEC_API_KEY": "sk-test"},
    )
    posts: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url.path).endswith("/repositories") and request.method == "GET":
            return httpx.Response(
                200,
                json={"repositories": [], "total": 0, "page": 1, "page_size": 100},
            )
        if str(request.url.path).endswith("/repositories") and request.method == "POST":
            posts.append(request.content)
            return httpx.Response(
                201,
                json={
                    **PROJECT,
                    "url": "https://github.com/new/repo",
                },
            )
        return httpx.Response(404, json={"detail": "not found"})

    api = ApiClient(cfg, transport=httpx.MockTransport(handler))
    try:
        project = resolve_or_register_by_url(api, "https://github.com/new/repo")
        assert project.url == "https://github.com/new/repo"
        assert posts
    finally:
        api.close()
