"""Tests for ``devsec k8s`` commands."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from devsec.main import app

runner = CliRunner()

_KUBECONFIG = (
    "apiVersion: v1\n"
    "kind: Config\n"
    "clusters:\n"
    "  - cluster:\n"
    "      server: https://127.0.0.1:6443\n"
    "    name: test\n"
    "contexts:\n"
    "  - context:\n"
    "      cluster: test\n"
    "      user: admin\n"
    "    name: test\n"
    "current-context: test\n"
    "users:\n"
    "  - name: admin\n"
    "    user:\n"
    "      token: test-token\n"
)


@pytest.fixture(autouse=True)
def k8s_auth(isolated_env):
    """Provide a test API key for k8s command tests."""
    import os
    os.environ["DEVSEC_API_KEY"] = "dk_test_key_for_cli_tests"
    yield
    os.environ.pop("DEVSEC_API_KEY", None)


@pytest.fixture
def kubeconfig_file(tmp_path: Path) -> Path:
    path = tmp_path / "config"
    path.write_text(_KUBECONFIG, encoding="utf-8")
    return path


def _mock_http(handler):
    import unittest.mock as mock

    original_client = httpx.Client

    def client_factory(**kwargs):
        kwargs.pop("transport", None)
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    return mock.patch("devsec.api.client.httpx.Client", client_factory)


def _auth_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/auth/me"):
        return httpx.Response(200, json={"id": "u1", "email": "t@t.com", "username": "t"})
    if request.url.path.endswith("/health"):
        return httpx.Response(200, json={"status": "healthy"})
    return httpx.Response(404)


def test_k8s_list_empty(isolated_env):
    def handler(request: httpx.Request) -> httpx.Response:
        if "/kubernetes/connections" in request.url.path:
            return httpx.Response(200, json=[])
        return _auth_handler(request)

    with _mock_http(handler):
        result = runner.invoke(app, ["k8s", "list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["clusters"] == []


def test_k8s_list_with_clusters(isolated_env):
    clusters = [{
        "id": "abc-123",
        "name": "prod",
        "cluster_name": "prod-cluster",
        "kind": "generic",
        "provider": "kubernetes",
        "kubernetes_version": "v1.30.0",
        "node_count": 4,
        "status": "connected",
        "health_status": "connected",
        "is_active": True,
    }]

    def handler(request: httpx.Request) -> httpx.Response:
        if "/kubernetes/connections" in request.url.path:
            return httpx.Response(200, json=clusters)
        return _auth_handler(request)

    with _mock_http(handler):
        result = runner.invoke(app, ["k8s", "list", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data["clusters"]) == 1
    assert data["clusters"][0]["cluster_name"] == "prod-cluster"


def test_k8s_config_connect(isolated_env, kubeconfig_file):
    encoded = base64.b64encode(_KUBECONFIG.encode()).decode()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/kubernetes/test"):
            return httpx.Response(200, json={
                "ok": True, "status": "connected",
                "kubernetes_version": "v1.30.0", "cluster_name": "test",
            })
        if request.url.path.endswith("/kubernetes/connect"):
            return httpx.Response(200, json={
                "id": "conn-1", "name": "test", "cluster_name": "test",
                "status": "connected", "kubernetes_version": "v1.30.0",
                "is_active": True, "kind": "generic",
            })
        return _auth_handler(request)

    with _mock_http(handler):
        result = runner.invoke(app, [
            "k8s", "config",
            "--kubeconfig", str(kubeconfig_file),
            "--name", "test-cluster",
            "--json",
        ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["connection"]["id"] == "conn-1"
    assert "test-token" not in result.stdout
    assert encoded[:20] not in result.stdout


def test_k8s_connect_eks_no_aws(isolated_env):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/kubernetes/eks/aws-available"):
            return httpx.Response(200, json={"available": False, "message": "No AWS connection"})
        return _auth_handler(request)

    with _mock_http(handler):
        result = runner.invoke(app, [
            "k8s", "connect", "--type", "eks",
            "--region", "us-east-1", "--cluster-name", "prod",
        ])
    assert result.exit_code != 0
    assert "AWS" in result.stderr or "aws" in result.stderr.lower()


def test_k8s_connect_aks_not_available(isolated_env):
    with _mock_http(_auth_handler):
        result = runner.invoke(app, ["k8s", "connect", "--type", "aks"])
    assert result.exit_code != 0
    assert "not yet available" in result.stderr.lower()


def test_k8s_connect_gke_not_available(isolated_env):
    with _mock_http(_auth_handler):
        result = runner.invoke(app, ["k8s", "connect", "--type", "gke"])
    assert result.exit_code != 0
    assert "not yet available" in result.stderr.lower()


def test_k8s_health(isolated_env):
    clusters = [{"id": "c1", "name": "prod", "is_active": True, "status": "connected"}]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/kubernetes/connections"):
            return httpx.Response(200, json=clusters)
        if "/health-score" in request.url.path:
            return httpx.Response(200, json={"overall": 85, "sub_scores": {"security": 70}})
        return _auth_handler(request)

    with _mock_http(handler):
        result = runner.invoke(app, ["k8s", "health", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["health_score"]["overall"] == 85


def test_k8s_security(isolated_env):
    clusters = [{"id": "c1", "name": "prod", "is_active": True}]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/kubernetes/connections"):
            return httpx.Response(200, json=clusters)
        if "/security-scan" in request.url.path:
            return httpx.Response(200, json={
                "findings": [{"rule_id": "K8S-SEC-PRIV", "severity": "high", "title": "Privileged", "namespace": "default", "resource": "pod/bad"}],
                "health_score": {"overall": 60},
            })
        return _auth_handler(request)

    with _mock_http(handler):
        result = runner.invoke(app, ["k8s", "security", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data["findings"]) == 1


def test_k8s_disconnect(isolated_env):
    clusters = [{"id": "c1", "name": "prod", "cluster_name": "prod", "is_active": True}]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/kubernetes/connections") and request.method == "GET":
            return httpx.Response(200, json=clusters)
        if request.url.path.endswith("/kubernetes/connections/c1") and request.method == "DELETE":
            return httpx.Response(200, json={"message": "Connection disconnected"})
        return _auth_handler(request)

    with _mock_http(handler):
        result = runner.invoke(app, ["k8s", "disconnect", "prod", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["disconnected"] == "c1"


def test_k8s_doctor(isolated_env, kubeconfig_file):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/kubernetes/test"):
            return httpx.Response(200, json={"ok": True, "status": "connected", "cluster_name": "test"})
        return _auth_handler(request)

    with _mock_http(handler):
        result = runner.invoke(app, [
            "k8s", "doctor",
            "--kubeconfig", str(kubeconfig_file),
            "--json",
        ])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["checks"]["cli"] is True
    assert "test-token" not in result.stdout


def test_kubernetes_alias(isolated_env):
    """``devsec kubernetes`` remains available as an alias."""
    def handler(request: httpx.Request) -> httpx.Response:
        if "/kubernetes/connections" in request.url.path:
            return httpx.Response(200, json=[])
        return _auth_handler(request)

    with _mock_http(handler):
        result = runner.invoke(app, ["kubernetes", "list", "--json"])
    assert result.exit_code == 0


def test_k8s_provider_factory():
    from devsec.k8s.providers import get_provider
    from devsec.k8s.providers.kubeconfig import KubeconfigProvider
    from devsec.k8s.providers.eks import EksProvider

    p = get_provider("kubeconfig", kubeconfig="/tmp/config")
    assert isinstance(p, KubeconfigProvider)
    p = get_provider("eks", region="us-west-2")
    assert isinstance(p, EksProvider)
