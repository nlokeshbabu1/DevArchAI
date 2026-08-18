"""MCP context service — public facade for live/external context.

Responsibilities:

- decide whether live context is needed (``requires_live_context``)
- fetch current context from the ordered providers for a technology
  (live environment data first, then current official docs)
- enforce per-technology timeouts, retries, and circuit breaking
- redact secrets on every payload before caching / persistence
- cache results in Redis (``devarchai:mcp:ctx:...``) and persist them to the
  ``mcp_context`` table for auditability
- **never raise**: any provider failure becomes a ``failed``/``timeout``/
  ``skipped`` result so the scan pipeline is never affected.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any

import structlog

from app.config import settings
from app.db.session import get_session_factory
from app.mcp.circuit_breaker import get_circuit_breaker
from app.mcp.providers import McpContextResult, McpProvider
from app.mcp.redaction import get_redactor
from app.mcp.router import get_mcp_router
from app.models.knowledge import McpContext
from app.rag.cache import get_rag_cache, mcp_cache_key
from app.services.metrics import (
    record_mcp_request,
    record_mcp_result,
)

logger = structlog.get_logger(__name__)


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _skipped(technology: str, provider: str, source_type: str, query: str, reason: str) -> McpContextResult:
    return McpContextResult(
        technology=technology,
        provider=provider,
        source_type=source_type,
        request_key=query,
        status="skipped",
        source_label=reason,
    )


class McpContextService:
    """Gateway to current/live external context."""

    def __init__(self) -> None:
        self._router = get_mcp_router()
        self._session_factory = get_session_factory()
        self._redactor = get_redactor()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def requires_live_context(
        self,
        technology: str,
        rule_id: str | None = None,
        *,
        connection_id: str | None = None,
    ) -> bool:
        return self._router.requires_live_context(
            technology, rule_id, connection_id=connection_id
        )

    def requires_docs_context(
        self,
        technology: str,
        rule_id: str | None = None,
        *,
        category: str | None = None,
    ) -> bool:
        """Whether current official documentation would improve the recommendation."""
        return self._router.requires_docs_context(
            technology, rule_id, category=category
        )

    async def get_live_context(
        self,
        technology: str,
        rule_id: str | None = None,
        query: str = "",
        *,
        connection_id: str | None = None,
        skip_cache: bool = False,
    ) -> list[McpContextResult]:
        """Fetch current context for a technology from its providers.

        Returns a list of results (never raises). Skips MCP entirely when
        disabled or when the circuit breaker for the technology is open.
        """
        if not self._router.is_enabled():
            return [
                _skipped(technology, "mcp", "live", query, "MCP disabled by configuration")
            ]

        breaker = get_circuit_breaker(technology)
        if not breaker.allow_request():
            record_mcp_result("skipped", 0.0)
            logger.warning("MCP_CIRCUIT_OPEN", technology=technology)
            return [
                _skipped(
                    technology, "mcp", "live", query,
                    f"circuit breaker open for technology '{technology}'; request skipped",
                )
            ]

        providers = self._router.providers_for(technology)
        results: list[McpContextResult] = []
        for provider in providers:
            result = await self._fetch_provider(provider, technology, query, connection_id, skip_cache)
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _fetch_provider(
        self,
        provider: McpProvider,
        technology: str,
        query: str,
        connection_id: str | None,
        skip_cache: bool,
    ) -> McpContextResult:
        request_key = query or f"tech:{technology}"
        cache_key = mcp_cache_key(technology, provider.name, request_key)

        if not skip_cache:
            cached = await get_rag_cache().get(cache_key)
            if cached is not None:
                logger.debug("MCP_CACHE_HIT", provider=provider.name, technology=technology)
                return McpContextResult(**cached)

        record_mcp_request(technology, provider.source_type)
        result = await self._fetch_with_retries(
            provider, technology, request_key, connection_id
        )

        # Defensive redaction: providers redact, but belt-and-braces before
        # the payload can be cached/persisted.
        result = McpContextResult(
            **{
                **result.to_dict(),
                "content": self._redactor.redact_text(result.content),
            }
        )

        breaker = get_circuit_breaker(technology)
        if result.status == "success":
            breaker.record_success()
        elif result.status in ("failed", "timeout"):
            breaker.record_failure()

        record_mcp_result(result.status, result.latency_ms or 0.0)

        if not skip_cache and result.status == "success":
            await get_rag_cache().set(
                cache_key, result.to_dict(), ttl_seconds=settings.MCP_CACHE_TTL_SECONDS
            )

        await self._persist(result)
        return result

    async def _fetch_with_retries(
        self,
        provider: McpProvider,
        technology: str,
        request_key: str,
        connection_id: str | None,
    ) -> McpContextResult:
        attempts = 1 + max(0, settings.MCP_MAX_RETRIES)
        for attempt in range(attempts):
            started = time.monotonic()
            try:
                result = await asyncio.wait_for(
                    provider.fetch(
                        technology, request_key, connection_id=connection_id
                    ),
                    timeout=settings.MCP_REQUEST_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                logger.warning(
                    "MCP_TIMEOUT", provider=provider.name, technology=technology, attempt=attempt + 1
                )
                result = McpContextResult(
                    technology=technology,
                    provider=provider.name,
                    source_type=provider.source_type,
                    request_key=request_key,
                    status="timeout",
                    source_label=f"{provider.name} timed out after {settings.MCP_REQUEST_TIMEOUT_SECONDS}s",
                )
            except Exception as exc:
                logger.warning(
                    "MCP_FAILURE",
                    provider=provider.name,
                    technology=technology,
                    attempt=attempt + 1,
                    error=str(exc)[:300],
                )
                result = McpContextResult(
                    technology=technology,
                    provider=provider.name,
                    source_type=provider.source_type,
                    request_key=request_key,
                    status="failed",
                    source_label=f"{provider.name} failed",
                    metadata={"error": str(exc)[:300]},
                )

            elapsed_ms = round((time.monotonic() - started) * 1000, 1)
            result = McpContextResult(**{**result.to_dict(), "latency_ms": elapsed_ms})

            if result.status in ("success", "skipped"):
                return result
            # failed/timeout → retry with backoff
            if attempt < attempts - 1:
                await asyncio.sleep(settings.MCP_RETRY_BACKOFF_SECONDS * (attempt + 1))
        return result

    async def _persist(self, result: McpContextResult) -> None:
        try:
            async with self._session_factory() as session:
                session.add(
                    McpContext(
                        technology=result.technology,
                        provider=result.provider,
                        source_type=result.source_type,
                        request_key=result.request_key[:128],
                        status=result.status,
                        content=result.content,
                        source_label=result.source_label[:512],
                        url=result.url[:1024],
                        latency_ms=result.latency_ms,
                        content_hash=_content_hash(result.content),
                        metadata_json=self._redactor.redact(result.metadata),
                    )
                )
                await session.commit()
        except Exception as exc:
            logger.debug("MCP_PERSIST_ERROR", error=str(exc)[:300])

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    async def stats(self) -> dict[str, Any]:
        from app.mcp.circuit_breaker import get_circuit_breaker_registry

        return {
            "enabled": self._router.is_enabled(),
            "router": self._router.stats(),
            "circuit_breakers": get_circuit_breaker_registry().stats(),
            "cache": await get_rag_cache().stats(),
        }


# Singleton
_mcp_service: McpContextService | None = None


def get_mcp_service() -> McpContextService:
    """Get the global MCP context service singleton."""
    global _mcp_service
    if _mcp_service is None:
        _mcp_service = McpContextService()
    return _mcp_service
