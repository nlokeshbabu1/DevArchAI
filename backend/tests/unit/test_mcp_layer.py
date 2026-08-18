"""Unit tests for the MCP live-context gateway (Phase 1).

Covers: secret redaction, per-technology circuit breaking, provider routing
(live vs docs), and the service facade guarantees (never raises, graceful
skips, retries/timeouts become results).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.mcp.circuit_breaker import CircuitBreaker
from app.mcp.providers import McpContextResult, McpProvider
from app.mcp.redaction import get_redactor
from app.mcp.router import McpRouter
from app.mcp.service import McpContextService

# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------

class TestSecretRedaction:
    def test_redacts_aws_keys(self):
        text = "key AKIA1234567890ABCDEF leaked"
        assert "AKIA1234567890ABCDEF" not in get_redactor().redact_text(text)

    def test_redacts_password_assignments(self):
        text = "db password=supersecret value"
        redacted = get_redactor().redact_text(text)
        assert "supersecret" not in redacted

    def test_redacts_bearer_and_jwt(self):
        text = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz and eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.x"
        redacted = get_redactor().redact_text(text)
        assert "Bearer" not in redacted or "abcdefghijklmnopqrstuvwxyz" not in redacted

    def test_redacts_private_keys(self):
        text = "-----BEGIN RSA PRIVATE KEY-----\nabc\n-----END RSA PRIVATE KEY-----"
        assert "RSA PRIVATE KEY" not in get_redactor().redact_text(text)

    def test_redacts_url_credentials(self):
        text = "host=https://user:secret@example.com/x"
        redacted = get_redactor().redact_text(text)
        assert "secret" not in redacted

    def test_redacts_structured_values(self):
        payload = {
            "ok": "fine",
            "token": "ghp_1234567890abcdef",
            "nested": {"password": "password=supersecret"},
            "items": [{"api_key": "sk_live_abcdefghijklmnop"}],
        }
        safe = get_redactor().redact(payload)
        assert safe["ok"] == "fine"
        assert safe["token"].startswith("[REDACTED]")
        assert safe["nested"]["password"].startswith("[REDACTED]")
        assert safe["items"][0]["api_key"].startswith("[REDACTED]")


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

class TestCircuitBreaker:
    def test_open_after_failures_and_recovers(self):
        breaker = CircuitBreaker("k8s", failure_threshold=2, cooldown_seconds=0.05)
        assert breaker.state.value == "closed"

        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state.value == "open"
        assert breaker.allow_request() is False

        # After cooldown, a single probe is allowed (half-open).
        import time

        time.sleep(0.06)
        assert breaker.allow_request() is True
        assert breaker.state.value == "half_open"

        breaker.record_success()
        assert breaker.state.value == "closed"

    def test_success_resets_failures(self):
        breaker = CircuitBreaker("docker", failure_threshold=5)
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()
        assert breaker.stats()["consecutive_failures"] == 0

    def test_stats(self):
        breaker = CircuitBreaker("k8s")
        stats = breaker.stats()
        assert stats["technology"] == "k8s"
        assert "state" in stats and "cooldown_seconds" in stats


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class StubProvider(McpProvider):
    def __init__(self, name, source_type):
        self._name = name
        self.source_type = source_type
        self.configured = True

    @property
    def name(self):
        return self._name

    def is_configured(self):
        return self.configured

    async def fetch(self, technology, query, **kwargs):
        return McpContextResult(
            technology=technology,
            provider=self.name,
            source_type=self.source_type,
            request_key=query,
            status="success",
            content="context",
        )


def _router_with(live_names=("live_aws",), doc_names=("official_docs",)):
    providers = [StubProvider(n, "live") for n in live_names] + [
        StubProvider(n, "docs") for n in doc_names
    ]
    return McpRouter(providers=providers)


class TestMcpRouter:
    def test_requires_live_for_aws(self):
        assert _router_with().requires_live_context("aws") is True

    def test_no_live_required_for_non_live_technology(self):
        assert _router_with().requires_live_context("kubernetes") is False

    def test_providers_ordered_live_then_docs(self):
        router = _router_with(live_names=("live_aws", "live_azure"), doc_names=("official_docs",))
        names = [p.name for p in router.providers_for("aws")]
        assert names == ["live_aws", "live_azure", "official_docs"]

    def test_unconfigured_providers_excluded(self):
        router = _router_with(doc_names=("official_docs",))
        router._providers[1].configured = False  # docs disabled
        assert [p.name for p in router.providers_for("docker")] == ["live_aws"]


# ---------------------------------------------------------------------------
# Service facade
# ---------------------------------------------------------------------------

class BoomProvider(McpProvider):
    source_type = "docs"

    @property
    def name(self):
        return "boom"

    async def fetch(self, technology, query, **kwargs):
        raise RuntimeError("provider exploded")


class SlowProvider(McpProvider):
    source_type = "docs"

    @property
    def name(self):
        return "slow"

    async def fetch(self, technology, query, **kwargs):
        import asyncio

        await asyncio.sleep(5)
        return McpContextResult(
            technology=technology, provider=self.name, source_type=self.source_type,
            request_key=query, status="success",
        )


class CapturingSession:
    def __init__(self):
        self.added = []
        self.committed = False

    async def execute(self, *a, **k):
        return None

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        self.committed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class CapturingFactory:
    def __init__(self):
        self.session = CapturingSession()

    def __call__(self):
        return self.session


def _service_with(provider, breaker_tech="aws", breaker=None):
    router = McpRouter(providers=[provider])
    svc = McpContextService()
    svc._router = router
    svc._session_factory = CapturingFactory()
    return svc


class TestMcpService:
    @pytest.mark.asyncio
    async def test_disabled_returns_skipped(self):
        # The router reads settings.MCP_ENABLED via app.mcp.router; the service
        # reads retry/timeout settings via app.mcp.service.
        with patch("app.mcp.service.settings") as s, patch("app.mcp.router.settings") as rs:
            s.MCP_ENABLED = False
            rs.MCP_ENABLED = False
            s.MCP_MAX_RETRIES = 0
            svc = _service_with(BoomProvider())
            results = await svc.get_live_context("aws")
        assert len(results) == 1
        assert results[0].status == "skipped"

    @pytest.mark.asyncio
    async def test_provider_failure_never_raises(self):
        with patch("app.mcp.service.settings") as s:
            s.MCP_ENABLED = True
            s.MCP_MAX_RETRIES = 0
            s.MCP_REQUEST_TIMEOUT_SECONDS = 1
            s.MCP_RETRY_BACKOFF_SECONDS = 0.01
            svc = _service_with(BoomProvider())
            results = await svc.get_live_context("aws")
        assert len(results) == 1
        assert results[0].status == "failed"

    @pytest.mark.asyncio
    async def test_success_persists_and_returns(self):
        with patch("app.mcp.service.settings") as s:
            s.MCP_ENABLED = True
            s.MCP_MAX_RETRIES = 0
            s.MCP_REQUEST_TIMEOUT_SECONDS = 1
            s.MCP_RETRY_BACKOFF_SECONDS = 0.01
            s.MCP_CACHE_TTL_SECONDS = 900
            svc = _service_with(StubProvider("docs_provider", "docs"))
            results = await svc.get_live_context("docker")
        assert len(results) == 1
        assert results[0].status == "success"
        assert svc._session_factory.session.committed is True

    @pytest.mark.asyncio
    async def test_circuit_open_short_circuits_to_skipped(self):
        breaker = CircuitBreaker("aws", failure_threshold=1, cooldown_seconds=60)
        breaker.record_failure()  # open now

        router = McpRouter(providers=[StubProvider("docs_provider", "docs")])
        svc = McpContextService()
        svc._router = router
        svc._session_factory = CapturingFactory()

        with patch("app.mcp.service.get_circuit_breaker", return_value=breaker):
            with patch("app.mcp.service.settings") as s:
                s.MCP_ENABLED = True
                s.MCP_MAX_RETRIES = 0
                results = await svc.get_live_context("aws")

        assert len(results) == 1
        assert results[0].status == "skipped"
        assert "circuit breaker" in results[0].source_label
