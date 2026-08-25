"""Optional integration tests against the production DevArchAI API.

Skipped unless DEVSEC_API_KEY is set. Never logs or prints secrets.
"""

from __future__ import annotations

import os

import httpx
import pytest

from devsec.api.client import ApiClient
from devsec.config import Config

PRODUCTION_API = os.environ.get("DEVSEC_API_URL", "https://backend.devarchai.xyz")
API_KEY = os.environ.get("DEVSEC_API_KEY", "")

pytestmark = pytest.mark.skipif(not API_KEY, reason="DEVSEC_API_KEY not set")


@pytest.fixture
def production_client() -> ApiClient:
    cfg = Config(env={"DEVSEC_API_URL": PRODUCTION_API, "DEVSEC_API_KEY": API_KEY})
    client = ApiClient(cfg)
    yield client
    client.close()


def test_production_health(production_client: ApiClient) -> None:
    response = production_client.get("/health")
    assert response.status_code == 200


def test_production_auth_me(production_client: ApiClient) -> None:
    payload = production_client.get_json("/auth/me")
    assert payload.get("email") or payload.get("id")


def test_production_scan_stages(production_client: ApiClient) -> None:
    payload = production_client.get_json("/scan/stages")
    stages = payload.get("stages") or []
    assert len(stages) >= 5
    ids = {stage.get("id") for stage in stages}
    assert "connecting_repository" in ids
    assert "scanning" in ids
