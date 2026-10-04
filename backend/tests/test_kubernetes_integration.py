"""
Tests for the Kubernetes integration routes (kubeconfig validation).
"""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.kubernetes.types import ConnectionStatus, ValidationResult
from app.main import app

client = TestClient(app)

NIL_UUID = "00000000-0000-0000-0000-000000000000"


def _valid_kubeconfig() -> str:
    return base64.b64encode(
        (
            "apiVersion: v1\n"
            "kind: Config\n"
            "clusters:\n"
            "  - cluster:\n"
            "      server: https://127.0.0.1:6443\n"
            "    name: local\n"
            "contexts:\n"
            "  - context:\n"
            "      cluster: local\n"
            "      user: admin\n"
            "    name: local\n"
            "users:\n"
            "  - name: admin\n"
            "    user:\n"
            "      token: abc\n"
        ).encode("utf-8")
    ).decode("ascii")


def _override_current_user() -> None:
    stub = MagicMock()
    stub.id = NIL_UUID
    stub.email = "qa@example.com"
    app.dependency_overrides[get_current_user] = lambda: stub


class TestKubernetesTestEndpoint:
    def setup_method(self):
        _override_current_user()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_valid_kubeconfig(self):
        with patch("app.api.v1.routes.kubernetes.validate_kubeconfig_text", new_callable=AsyncMock) as mock_val:
            mock_val.return_value = ValidationResult(
                status=ConnectionStatus.CONNECTED,
                kubernetes_version="v1.34",
                cluster_name="local",
            )
            response = client.post(
                "/api/v1/kubernetes/test",
                json={"name": "test-cluster", "kubeconfig": _valid_kubeconfig()},
            )
            assert response.status_code == 200
            assert response.json()["ok"] is True

    def test_missing_clusters_section(self):
        bad = base64.b64encode(b"kind: Config\ncontexts: []").decode("ascii")
        response = client.post(
            "/api/v1/kubernetes/test",
            json={"name": "test-cluster", "kubeconfig": bad},
        )
        assert response.status_code == 400
        assert "clusters" in response.text

    def test_invalid_base64(self):
        response = client.post(
            "/api/v1/kubernetes/test",
            json={"name": "test-cluster", "kubeconfig": "%%%not-base64%%%"},
        )
        assert response.status_code == 400

    def test_missing_kubeconfig(self):
        response = client.post(
            "/api/v1/kubernetes/test",
            json={"name": "test-cluster"},
        )
        assert response.status_code == 422


class TestIntegrationConnectUrl:
    """Connect-mode OAuth URL endpoints (no DB required)."""

    def setup_method(self):
        _override_current_user()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_github_url_returns_contract(self):
        response = client.get("/api/v1/integrations/github/url")
        assert response.status_code == 200
        body = response.json()
        assert "oauth_url" in body
        assert "state" in body

    def test_gitlab_url_returns_contract(self):
        response = client.get("/api/v1/integrations/gitlab/url")
        assert response.status_code == 200
        body = response.json()
        assert "oauth_url" in body
        assert "state" in body
