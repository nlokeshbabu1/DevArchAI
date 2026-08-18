"""Technology router for the MCP live-context gateway.

Decides, for a given technology (and optionally rule), whether live external
context is needed and which providers to consult. Follows the knowledge
priority order: live environment data first, then current official docs.

Routing is per-technology so a request for ``aws`` consults the live AWS
provider before docs, while a request for ``docker`` consults docs directly.
"""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.mcp.providers import McpProvider, default_providers
from app.rag.inventory import get_inventory

# Technologies whose context is primarily *live environment data* (AWS/Azure).
LIVE_CONTEXT_TECHNOLOGIES = {"aws", "azure"}

# All technologies that benefit from current official documentation.
# MCP is triggered for these when the finding requires version-specific or
# configuration-specific knowledge that may change over time.
DOCS_CONTEXT_TECHNOLOGIES = {
    "kubernetes",
    "helm",
    "terraform",
    "docker",
    "github_actions",
    "gitlab_ci",
    "jenkins",
    "circleci",
    "azure_devops",
    "ansible",
    "prometheus",
    "grafana",
}

# Rule categories where current documentation adds the most value.
# Best-practice and general-security rules tend to be stable; configuration
# and deployment rules benefit from up-to-date references.
MCP_BENEFITING_CATEGORIES = {
    "security",
    "configuration",
    "deployment",
    "pipeline",
    "infrastructure",
    "scaling",
    "monitoring",
    "cost",
}


class McpRouter:
    """Maps technologies to ordered MCP context providers."""

    def __init__(self, providers: list[McpProvider] | None = None) -> None:
        self._providers = providers or default_providers()
        self._providers_by_name = {p.name: p for p in self._providers}

    # ------------------------------------------------------------------
    # Provider selection
    # ------------------------------------------------------------------

    def is_enabled(self) -> bool:
        return settings.MCP_ENABLED

    def providers_for(self, technology: str) -> list[McpProvider]:
        """Configured providers applicable to a technology, in priority order.

        Global provider order is live-first then docs, so a technology gets
        live environment data before current official documentation.
        """
        return [p for p in self._providers if p.is_configured()]

    def requires_live_context(
        self,
        technology: str,
        rule_id: str | None = None,
        *,
        connection_id: str | None = None,
    ) -> bool:
        """Whether live environment data is the primary context source.

        True when the technology is a live-context technology (aws/azure), MCP
        is enabled, a live provider is configured, and either a connection is
        available or no connection was required.
        """
        if not self.is_enabled():
            return False
        if technology not in LIVE_CONTEXT_TECHNOLOGIES:
            return False
        live_providers = [
            p for p in self.providers_for(technology) if p.source_type == "live"
        ]
        if not live_providers:
            return False
        return True

    def requires_docs_context(
        self,
        technology: str,
        rule_id: str | None = None,
        *,
        category: str | None = None,
    ) -> bool:
        """Whether current official documentation would improve the recommendation.

        Returns True when:
        1. MCP is enabled
        2. The technology has official documentation available
        3. The rule category benefits from current documentation

        This is a broader check than ``requires_live_context`` — it covers all
        supported DevOps technologies, not just cloud providers.
        """
        if not self.is_enabled():
            return False
        if technology not in DOCS_CONTEXT_TECHNOLOGIES:
            return False
        if category and category.lower() not in MCP_BENEFITING_CATEGORIES:
            return False
        return True

    def technology_for_rule_id(self, rule_id: str) -> list[str]:
        return get_inventory().technology_for_rule_id(rule_id)

    def normalize_technology(self, technology: str | None) -> str | None:
        """Resolve a technology alias to a canonical provider key."""
        if not technology:
            return None
        return technology

    def stats(self) -> dict[str, Any]:
        return {
            "enabled": self.is_enabled(),
            "providers": [
                {"name": p.name, "source_type": p.source_type, "configured": p.is_configured()}
                for p in self._providers
            ],
            "live_context_technologies": sorted(LIVE_CONTEXT_TECHNOLOGIES),
            "docs_context_technologies": sorted(DOCS_CONTEXT_TECHNOLOGIES),
            "mcp_benefiting_categories": sorted(MCP_BENEFITING_CATEGORIES),
        }


# Singleton
_router: McpRouter | None = None


def get_mcp_router() -> McpRouter:
    """Get the global MCP router singleton."""
    global _router
    if _router is None:
        _router = McpRouter()
    return _router
