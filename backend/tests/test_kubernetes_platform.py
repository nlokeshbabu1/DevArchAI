"""Tests for Kubernetes platform modules."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.kubernetes.health_score import compute_health_score
from app.kubernetes.security_analyzer import analyze_cluster_security
from app.kubernetes.types import ClusterOverview, ConnectionStatus, ValidationResult
from app.kubernetes.version_advisor import build_version_advisor


def _valid_kubeconfig() -> str:
    return (
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
    )


class TestVersionAdvisor:
    def test_upgrade_recommended_for_old_version(self):
        result = build_version_advisor("v1.29", provider="kubernetes", kind="generic")
        assert result["upgrade_status"] == "upgrade_recommended"
        assert result["recommended_version"] == "v1.34"

    def test_supported_current_version(self):
        result = build_version_advisor("v1.34", provider="kubernetes", kind="generic")
        assert result["upgrade_status"] == "supported"


class TestHealthScore:
    def test_evidence_based_scores(self):
        overview = ClusterOverview(
            nodes_total=6,
            nodes_ready=5,
            nodes_not_ready=1,
            pods_total=142,
            pods_running=128,
            pods_failed=4,
            pods_crash_loop=2,
        )
        score = compute_health_score(
            overview=overview,
            security_findings=[{"severity": "high", "rule_id": "K8S-SEC-PRIV"}],
            version_advisor={"upgrade_status": "upgrade_recommended", "impact_summary": "HIGH"},
            connection_status="connected",
        )
        assert "overall" in score
        assert score["sub_scores"]["availability"] < 100
        assert len(score["evidence"]["availability"]) > 0


class TestSecurityAnalyzer:
    def test_detects_privileged_container(self):
        pod = MagicMock()
        pod.metadata.namespace = "default"
        pod.metadata.name = "bad-pod"
        pod.spec.host_network = False
        pod.spec.host_pid = False
        pod.spec.volumes = []
        pod.spec.security_context = None

        cs = MagicMock()
        cs.name = "app"
        cs.ready = False
        cs.restart_count = 0
        cs.image = "nginx:latest"
        cs.state.waiting = None
        cs.state.terminated = None
        pod.status.container_statuses = [cs]

        container = MagicMock()
        container.name = "app"
        container.image = "nginx:latest"
        container.security_context = MagicMock(privileged=True, run_as_user=None)
        container.resources = None
        container.liveness_probe = None
        container.readiness_probe = None
        pod.spec.containers = [container]

        findings = analyze_cluster_security([pod], [])
        assert any(f["rule_id"] == "K8S-SEC-PRIV" for f in findings)


class TestKubernetesTestEndpoint:
    def setup_method(self):
        from app.core.security import get_current_user
        from app.main import app

        stub = MagicMock()
        stub.id = "00000000-0000-0000-0000-000000000000"
        stub.email = "qa@example.com"
        app.dependency_overrides[get_current_user] = lambda: stub
        self.app = app

    def teardown_method(self):
        self.app.dependency_overrides.clear()

    def test_test_endpoint_with_mock_validation(self):
        from fastapi.testclient import TestClient

        client = TestClient(self.app)
        encoded = base64.b64encode(_valid_kubeconfig().encode()).decode()

        with patch("app.api.v1.routes.kubernetes.validate_kubeconfig_text", new_callable=AsyncMock) as mock_val:
            mock_val.return_value = ValidationResult(
                status=ConnectionStatus.CONNECTED,
                kubernetes_version="v1.34",
                cluster_name="local",
            )
            response = client.post(
                "/api/v1/kubernetes/test",
                json={"name": "test", "kubeconfig": encoded},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["ok"] is True
            assert body["kubernetes_version"] == "v1.34"

    def test_invalid_base64(self):
        from fastapi.testclient import TestClient

        client = TestClient(self.app)
        response = client.post(
            "/api/v1/kubernetes/test",
            json={"name": "test", "kubeconfig": "%%%not-base64%%%"},
        )
        assert response.status_code == 400


class TestClusterCache:
    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        from app.kubernetes.cache import ClusterCache

        cache = ClusterCache()
        result = await cache.get_snapshot("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_json_passes_timedelta_to_redis(self):
        from datetime import timedelta
        from unittest.mock import AsyncMock, MagicMock

        from app.kubernetes.cache import ClusterCache, RECOMMENDATION_TTL

        cache = ClusterCache()
        mock_redis = MagicMock()
        mock_redis.is_connected = True
        mock_redis.set = AsyncMock(return_value=True)
        cache._redis = AsyncMock(return_value=mock_redis)

        payload = {"finding": "test", "source": "llm"}
        await cache.set_recommendation("K8S-TROUBLESHOOT", "abc123", payload)

        mock_redis.set.assert_awaited_once()
        _key, cached_value, *_rest = mock_redis.set.await_args.args
        ttl = mock_redis.set.await_args.kwargs["ttl"]
        assert cached_value == payload
        assert ttl == timedelta(seconds=RECOMMENDATION_TTL)


class TestClusterAILlmBudget:
    @pytest.mark.asyncio
    async def test_analyze_findings_caps_llm_calls(self):
        from app.ai.context_engine import AIRecommendation
        from app.kubernetes.cluster_ai_engine import ClusterAIEngine

        engine = ClusterAIEngine()
        findings = [
            {"rule_id": "K8S-A", "title": "Low", "severity": "low"},
            {"rule_id": "K8S-B", "title": "High", "severity": "high"},
            {"rule_id": "K8S-C", "title": "Critical", "severity": "critical"},
        ]
        snapshot = {"pods": [], "security_findings": findings}
        llm_calls = 0

        async def fake_generate(proxy, context, fp):
            nonlocal llm_calls
            llm_calls += 1
            return AIRecommendation(
                finding_fingerprint=fp,
                rule_id=proxy.rule_id,
                technology="kubernetes",
                summary="LLM summary",
                risk="high",
                impact="high",
                ai_explanation="Root cause from LLM",
                fix_code="",
                fix_example="kubectl rollout restart",
                full_example="",
                best_practices=["Review pod logs"],
                confidence=0.9,
                documentation_url="",
                ai_generated=True,
                source="llm",
            )

        engine._context_engine.generate_recommendation = fake_generate
        engine._context_engine.build_context = AsyncMock(return_value=MagicMock())

        with patch.object(engine._cache, "get_recommendation", AsyncMock(return_value=None)), patch.object(
            engine._cache, "set_recommendation", AsyncMock()
        ):
            result = await engine.analyze_findings(
                findings, snapshot, max_findings=3, max_llm_calls=1
            )

        assert llm_calls == 1
        assert result.recommendation_count == 3
        sources = {r["source"] for r in result.recommendations}
        assert "llm" in sources
        assert "deterministic" in sources

    @pytest.mark.asyncio
    async def test_rate_limit_circuit_skips_llm(self):
        from app.ai import context_engine
        from app.kubernetes.cluster_ai_engine import ClusterAIEngine

        context_engine.mark_llm_rate_limited(120)
        engine = ClusterAIEngine()
        findings = [{"rule_id": "K8S-X", "title": "Test", "severity": "high"}]

        with patch.object(engine._cache, "get_recommendation", AsyncMock(return_value=None)), patch.object(
            engine._cache, "set_recommendation", AsyncMock()
        ), patch.object(
            engine._context_engine, "generate_recommendation", AsyncMock()
        ) as mock_llm:
            result = await engine.analyze_findings(findings, {"pods": []}, max_llm_calls=5)

        mock_llm.assert_not_awaited()
        assert result.recommendations[0]["source"] == "deterministic"
        context_engine._llm_rate_limited_until = 0.0
