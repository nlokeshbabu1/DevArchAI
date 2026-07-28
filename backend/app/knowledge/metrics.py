"""Knowledge retrieval metrics and observability.

Provides metrics collection and monitoring for the knowledge retrieval layer.
Tracks provider performance, cache hit rates, and retrieval latency.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProviderMetrics:
    """Metrics for a single knowledge provider."""

    provider_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0
    total_documents: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def avg_latency_ms(self) -> float:
        """Average latency in milliseconds."""
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate as a percentage."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100


@dataclass
class KnowledgeRetrievalMetrics:
    """Aggregate metrics for the knowledge retrieval system."""

    total_retrievals: int = 0
    total_documents_retrieved: int = 0
    total_latency_ms: float = 0.0
    provider_metrics: dict[str, ProviderMetrics] = field(default_factory=dict)
    _start_time: float = field(default_factory=time.time)

    def record_provider_request(
        self,
        provider_name: str,
        latency_ms: float,
        success: bool,
        document_count: int = 0,
        cache_hit: bool = False,
    ) -> None:
        """Record a provider request."""
        if provider_name not in self.provider_metrics:
            self.provider_metrics[provider_name] = ProviderMetrics(
                provider_name=provider_name,
            )

        pm = self.provider_metrics[provider_name]
        pm.total_requests += 1
        pm.total_latency_ms += latency_ms
        pm.min_latency_ms = min(pm.min_latency_ms, latency_ms)
        pm.max_latency_ms = max(pm.max_latency_ms, latency_ms)

        if success:
            pm.successful_requests += 1
            pm.total_documents += document_count
        else:
            pm.failed_requests += 1

        if cache_hit:
            pm.cache_hits += 1
        else:
            pm.cache_misses += 1

        self.total_retrievals += 1
        self.total_documents_retrieved += document_count
        self.total_latency_ms += latency_ms

    def get_summary(self) -> dict[str, Any]:
        """Get summary metrics."""
        uptime_seconds = time.time() - self._start_time
        return {
            "uptime_seconds": round(uptime_seconds, 1),
            "total_retrievals": self.total_retrievals,
            "total_documents_retrieved": self.total_documents_retrieved,
            "avg_latency_ms": round(
                self.total_latency_ms / max(self.total_retrievals, 1), 1
            ),
            "retrievals_per_minute": round(
                self.total_retrievals / max(uptime_seconds / 60, 0.1), 1
            ),
            "providers": {
                name: {
                    "total_requests": pm.total_requests,
                    "success_rate": round(pm.success_rate, 1),
                    "avg_latency_ms": round(pm.avg_latency_ms, 1),
                    "cache_hit_rate": round(pm.cache_hit_rate, 1),
                    "total_documents": pm.total_documents,
                }
                for name, pm in self.provider_metrics.items()
            },
        }

    def log_summary(self) -> None:
        """Log a summary of all metrics."""
        summary = self.get_summary()
        logger.info(
            "KNOWLEDGE_RETRIEVAL_METRICS",
            **summary,
        )


# Singleton
_metrics: KnowledgeRetrievalMetrics | None = None


def get_knowledge_metrics() -> KnowledgeRetrievalMetrics:
    """Get the singleton metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = KnowledgeRetrievalMetrics()
    return _metrics


class MetricsCollector:
    """Context manager for collecting metrics on knowledge retrieval operations."""

    def __init__(self, provider_name: str, query: str = ""):
        self.provider_name = provider_name
        self.query = query
        self.start_time: float = 0.0
        self.document_count: int = 0
        self.success: bool = False
        self.cache_hit: bool = False
        self._metrics = get_knowledge_metrics()

    def __enter__(self) -> MetricsCollector:
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        latency_ms = (time.time() - self.start_time) * 1000

        if exc_type is not None:
            self.success = False
            logger.warning(
                "KNOWLEDGE_RETRIEVAL_FAILED",
                provider=self.provider_name,
                query=self.query[:80],
                error=str(exc_val),
                latency_ms=round(latency_ms, 1),
            )
        else:
            self.success = True

        self._metrics.record_provider_request(
            provider_name=self.provider_name,
            latency_ms=latency_ms,
            success=self.success,
            document_count=self.document_count,
            cache_hit=self.cache_hit,
        )

    def set_documents(self, count: int) -> None:
        """Set the number of documents retrieved."""
        self.document_count = count

    def set_cache_hit(self, hit: bool) -> None:
        """Set whether this was a cache hit."""
        self.cache_hit = hit
