"""Unit tests for the MCP router and context decision logic."""
import pytest
from unittest.mock import MagicMock, patch


class TestMcpRouter:
    """Tests for McpRouter technology decision logic."""

    @pytest.fixture
    def router(self):
        """Provide a fresh McpRouter with mock providers."""
        from app.mcp.router import McpRouter, get_mcp_router
        # Reset singleton for test isolation
        import app.mcp.router as mod
        mod._mcp_router_instance = None
        return McpRouter()

    def test_is_enabled_when_mcp_true(self, router):
        """Router is enabled when MCP_ENABLED=True."""
        with patch("app.mcp.router.settings") as mock_settings:
            mock_settings.MCP_ENABLED = True
            assert router.is_enabled() is True

    def test_is_disabled_when_mcp_false(self, router):
        """Router is disabled when MCP_ENABLED=False."""
        with patch("app.mcp.router.settings") as mock_settings:
            mock_settings.MCP_ENABLED = False
            assert router.is_enabled() is False

    def test_requires_live_context_aws(self, router):
        """AWS requires live context (has live providers)."""
        with patch("app.mcp.router.settings") as mock_settings:
            mock_settings.MCP_ENABLED = True
            provider = MagicMock()
            provider.source_type = "live"
            provider.is_available.return_value = True
            router._providers = [provider]
            assert router.requires_live_context("aws") is True

    def test_requires_live_context_kubernetes_false(self, router):
        """Kubernetes does NOT require live context (docs only)."""
        with patch("app.mcp.router.settings") as mock_settings:
            mock_settings.MCP_ENABLED = True
            assert router.requires_live_context("kubernetes") is False

    def test_requires_docs_context_kubernetes(self, router):
        """Kubernetes triggers docs context lookup."""
        with patch("app.mcp.router.settings") as mock_settings:
            mock_settings.MCP_ENABLED = True
            assert router.requires_docs_context("kubernetes") is True

    def test_requires_docs_context_docker(self, router):
        """Docker triggers docs context lookup."""
        with patch("app.mcp.router.settings") as mock_settings:
            mock_settings.MCP_ENABLED = True
            assert router.requires_docs_context("docker") is True

    def test_requires_docs_context_terraform(self, router):
        """Terraform triggers docs context lookup."""
        with patch("app.mcp.router.settings") as mock_settings:
            mock_settings.MCP_ENABLED = True
            assert router.requires_docs_context("terraform") is True

    def test_requires_docs_context_unknown_tech(self, router):
        """Unknown technology does NOT trigger docs context."""
        with patch("app.mcp.router.settings") as mock_settings:
            mock_settings.MCP_ENABLED = True
            assert router.requires_docs_context("randomlib") is False

    def test_requires_docs_context_with_category(self, router):
        """Category filtering: security category triggers docs for kubernetes."""
        with patch("app.mcp.router.settings") as mock_settings:
            mock_settings.MCP_ENABLED = True
            assert router.requires_docs_context("kubernetes", category="security") is True
            assert router.requires_docs_context("kubernetes", category="unknown") is False

    def test_requires_docs_context_disabled(self, router):
        """When MCP disabled, no docs context needed."""
        with patch("app.mcp.router.settings") as mock_settings:
            mock_settings.MCP_ENABLED = False
            assert router.requires_docs_context("kubernetes") is False

    def test_providers_for_returns_all(self, router):
        """providers_for returns all providers for a technology."""
        with patch("app.mcp.router.settings") as mock_settings:
            mock_settings.MCP_ENABLED = True
            p1 = MagicMock()
            p1.source_type = "live"
            p2 = MagicMock()
            p2.source_type = "docs"
            router._providers = [p1, p2]
            result = router.providers_for("kubernetes")
            assert len(result) == 2

    def test_normalize_technology(self, router):
        """normalize_technology passes through as-is."""
        assert router.normalize_technology(None) is None
        assert router.normalize_technology("Kubernetes") == "Kubernetes"
        assert router.normalize_technology("AWS") == "AWS"

    def test_stats(self, router):
        """stats returns router statistics dict."""
        with patch("app.mcp.router.settings") as mock_settings:
            mock_settings.MCP_ENABLED = True
            stats = router.stats()
            assert "enabled" in stats
            assert "providers" in stats
            assert isinstance(stats["providers"], list)


class TestMcpRouterConstants:
    """Tests for the router technology set constants."""

    def test_docs_context_technologies_count(self):
        """Verify the exact set of docs context technologies."""
        from app.mcp.router import DOCS_CONTEXT_TECHNOLOGIES
        expected = {
            "kubernetes", "helm", "terraform", "docker",
            "github_actions", "gitlab_ci", "jenkins", "circleci",
            "azure_devops", "ansible", "prometheus", "grafana"
        }
        assert DOCS_CONTEXT_TECHNOLOGIES == expected

    def test_live_context_technologies(self):
        """Verify live context technologies (AWS and Azure only)."""
        from app.mcp.router import LIVE_CONTEXT_TECHNOLOGIES
        assert LIVE_CONTEXT_TECHNOLOGIES == {"aws", "azure"}

    def test_mcp_benefiting_categories(self):
        """Verify the set of MCP-benefiting categories."""
        from app.mcp.router import MCP_BENEFITING_CATEGORIES
        assert "security" in MCP_BENEFITING_CATEGORIES
        assert "configuration" in MCP_BENEFITING_CATEGORIES
        assert "deployment" in MCP_BENEFITING_CATEGORIES
        assert "pipeline" in MCP_BENEFITING_CATEGORIES
        assert "cost" in MCP_BENEFITING_CATEGORIES
