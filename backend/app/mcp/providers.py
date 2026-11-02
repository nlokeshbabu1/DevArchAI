"""MCP context providers.

Providers source "current/external" information — distinct from RAG ("what
DevArchAI knows"). Provider priority follows the knowledge priority order:

1. Live environment data (AWS / Azure scan state).
2. Current official documentation (fetched from curated official URLs).
3. DevArchAI curated knowledge (handled by the RAG layer, not here).
4. General external knowledge (extension point).

Every provider returns an :class:`McpContextResult`. Failures are captured as
a ``status`` (failure/timeout/skipped) — providers never raise, so a broken
provider can never fail the scan pipeline.
"""

from __future__ import annotations

import html
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog

from app.config import settings
from app.mcp.redaction import get_redactor

logger = structlog.get_logger(__name__)

MAX_CONTENT_CHARS = 6000


@dataclass(frozen=True)
class McpContextResult:
    """A single MCP-provided context payload."""

    technology: str
    provider: str
    source_type: str  # live | docs
    request_key: str
    status: str  # success | failed | timeout | skipped
    content: str = ""
    source_label: str = ""
    url: str = ""
    latency_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "technology": self.technology,
            "provider": self.provider,
            "source_type": self.source_type,
            "request_key": self.request_key,
            "status": self.status,
            "content": self.content,
            "source_label": self.source_label,
            "url": self.url,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
        }


class McpProvider(ABC):
    """Abstract MCP context provider."""

    source_type = "docs"

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    def is_configured(self) -> bool:
        return True

    @abstractmethod
    async def fetch(self, technology: str, query: str, **kwargs: Any) -> McpContextResult:
        ...


def _strip_html(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# Curated map of current official documentation URLs per technology.
OFFICIAL_DOC_URLS: dict[str, list[str]] = {
    "kubernetes": [
        "https://kubernetes.io/docs/concepts/security/",
        "https://kubernetes.io/docs/tasks/configure-pod-container/security-context/",
    ],
    "terraform": [
        "https://developer.hashicorp.com/terraform/language/syntax/configuration",
        "https://developer.hashicorp.com/terraform/tutorials/configuration-language/sensitive-variables",
    ],
    "docker": [
        "https://docs.docker.com/develop/develop-images/dockerfile_best-practices/",
        "https://docs.docker.com/engine/security/",
    ],
    "helm": [
        "https://helm.sh/docs/topics/chart_best_practices/",
    ],
    "github_actions": [
        "https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions",
    ],
    "gitlab_ci": [
        "https://docs.gitlab.com/ci/",
    ],
    "jenkins": [
        "https://www.jenkins.io/doc/book/pipeline/",
    ],
    "circleci": [
        "https://circleci.com/docs/",
    ],
    "azure_devops": [
        "https://learn.microsoft.com/en-us/azure/devops/pipelines/",
    ],
    "ansible": [
        "https://docs.ansible.com/ansible/latest/playbook_guide/index.html",
    ],
    "prometheus": [
        "https://prometheus.io/docs/prometheus/latest/configuration/",
    ],
    "grafana": [
        "https://grafana.com/docs/grafana/latest/",
    ],
    "aws": [
        "https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html",
    ],
    "azure": [
        "https://learn.microsoft.com/en-us/azure/security/",
    ],
}


class OfficialDocsProvider(McpProvider):
    """Fetches current official documentation for a technology."""

    source_type = "docs"

    def __init__(self, urls: dict[str, list[str]] | None = None) -> None:
        self._urls = urls or OFFICIAL_DOC_URLS

    @property
    def name(self) -> str:
        return "official_docs"

    def is_configured(self) -> bool:
        return settings.MCP_DOCS_ENABLED

    async def fetch(self, technology: str, query: str, **kwargs: Any) -> McpContextResult:
        urls = self._urls.get(technology, [])
        if not urls:
            return McpContextResult(
                technology=technology,
                provider=self.name,
                source_type=self.source_type,
                request_key=query,
                status="skipped",
                source_label="no curated official doc URL for this technology",
            )

        url = urls[0]
        try:
            async with httpx.AsyncClient(
                timeout=settings.MCP_REQUEST_TIMEOUT_SECONDS,
                follow_redirects=True,
            ) as client:
                response = await client.get(url, headers={"User-Agent": "DevArchAI/1.0"})
                response.raise_for_status()
                content = _strip_html(response.text)[:MAX_CONTENT_CHARS]
        except httpx.TimeoutException:
            return McpContextResult(
                technology=technology,
                provider=self.name,
                source_type=self.source_type,
                request_key=query,
                status="timeout",
                source_label=f"official documentation request timed out: {url}",
                url=url,
            )
        except Exception as exc:
            return McpContextResult(
                technology=technology,
                provider=self.name,
                source_type=self.source_type,
                request_key=query,
                status="failed",
                source_label=f"failed to fetch official documentation: {url}",
                url=url,
                metadata={"error": str(exc)[:300]},
            )

        content = get_redactor().redact_text(content)
        return McpContextResult(
            technology=technology,
            provider=self.name,
            source_type=self.source_type,
            request_key=query,
            status="success",
            content=content,
            source_label=f"official documentation ({url})",
            url=url,
        )


class LiveAwsProvider(McpProvider):
    """Live AWS context sourced from the existing cloud scan state.

    Uses already-stored cloud scan data (the same tables the AWS live scanners
    write to) — no new AWS API calls, no new credentials. When no connection or
    recent scan exists it reports ``skipped`` so the pipeline is unaffected.
    """

    source_type = "live"

    @property
    def name(self) -> str:
        return "live_aws"

    def is_configured(self) -> bool:
        return settings.MCP_LIVE_AWS_ENABLED

    async def fetch(self, technology: str, query: str, **kwargs: Any) -> McpContextResult:
        connection_id = kwargs.get("connection_id")
        if not connection_id:
            return McpContextResult(
                technology=technology,
                provider=self.name,
                source_type=self.source_type,
                request_key=query,
                status="skipped",
                source_label="no cloud connection id provided for live AWS context",
            )
        try:
            from sqlalchemy import text as sql_text

            from app.db.session import get_session_factory

            async with get_session_factory()() as session:
                result = await session.execute(
                    sql_text(
                        """
                        SELECT cf.service, cf.resource_type, cf.title, cf.severity,
                               cf.recommendation
                        FROM cloud_findings cf
                        JOIN cloud_scan_sessions cs ON cs.id = cf.scan_session_id
                        WHERE cs.connection_id = :conn
                          AND cf.severity IN ('critical', 'high')
                        ORDER BY cf.created_at DESC
                        LIMIT 25
                        """
                    ),
                    {"conn": connection_id},
                )
                rows = result.fetchall()
        except Exception as exc:
            return McpContextResult(
                technology=technology,
                provider=self.name,
                source_type=self.source_type,
                request_key=query,
                status="failed",
                source_label="live AWS context unavailable",
                metadata={"error": str(exc)[:300]},
            )

        if not rows:
            return McpContextResult(
                technology=technology,
                provider=self.name,
                source_type=self.source_type,
                request_key=query,
                status="skipped",
                source_label="no live AWS scan findings for this connection",
            )

        content_lines = [f"Live AWS findings (connection {connection_id}):"]
        for service, resource_type, title, severity, recommendation in rows:
            content_lines.append(f"- [{severity}] {service}/{resource_type}: {title}")
            if recommendation:
                content_lines.append(f"  Recommended: {recommendation[:200]}")
        content = get_redactor().redact_text("\n".join(content_lines)[:MAX_CONTENT_CHARS])

        return McpContextResult(
            technology=technology,
            provider=self.name,
            source_type=self.source_type,
            request_key=query,
            status="success",
            content=content,
            source_label=f"live AWS findings (connection {connection_id})",
        )


class LiveAzureProvider(McpProvider):
    """Live Azure context sourced from existing cloud scan state (extension point)."""

    source_type = "live"

    @property
    def name(self) -> str:
        return "live_azure"

    def is_configured(self) -> bool:
        return settings.MCP_LIVE_AZURE_ENABLED

    async def fetch(self, technology: str, query: str, **kwargs: Any) -> McpContextResult:
        return McpContextResult(
            technology=technology,
            provider=self.name,
            source_type=self.source_type,
            request_key=query,
            status="skipped",
            source_label="live Azure context not yet wired for this phase",
        )


# Provider registry: live providers first (priority order), then docs.
def default_providers() -> list[McpProvider]:
    return [LiveAwsProvider(), LiveAzureProvider(), OfficialDocsProvider()]
