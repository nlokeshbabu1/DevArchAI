"""
Prometheus Metrics Export for DevArchAI

Provides application-level metrics for monitoring:
- Scan duration
- AI success rate
- Findings count
- Error rates
- Cache hit/miss rates

Usage:
    GET /metrics
    
Returns Prometheus-compatible metrics
"""


import structlog
from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

logger = structlog.get_logger(__name__)

# Create custom registry
registry = CollectorRegistry()

# ============================================================================
# SCAN METRICS
# ============================================================================

scan_total = Counter(
    'devarchai_scan_total',
    'Total number of scans executed',
    ['status', 'technology'],
    registry=registry,
)

scan_duration_seconds = Histogram(
    'devarchai_scan_duration_seconds',
    'Time spent executing scans',
    buckets=[10, 30, 60, 120, 300, 600, 1200],
    registry=registry,
)

scan_active = Gauge(
    'devarchai_scan_active',
    'Number of currently running scans',
    registry=registry,
)

# ============================================================================
# AI METRICS
# ============================================================================

ai_requests_total = Counter(
    'devarchai_ai_requests_total',
    'Total AI API requests',
    ['provider', 'status'],  # status: success, failure, fallback
    registry=registry,
)

ai_response_time_seconds = Histogram(
    'devarchai_ai_response_time_seconds',
    'AI provider response time',
    ['provider'],
    buckets=[0.5, 1, 2, 5, 10, 30],
    registry=registry,
)

ai_success_rate = Gauge(
    'devarchai_ai_success_rate',
    'AI success rate percentage',
    ['provider'],
    registry=registry,
)

# ============================================================================
# FINDINGS METRICS
# ============================================================================

findings_total = Counter(
    'devarchai_findings_total',
    'Total findings detected',
    ['severity', 'category'],
    registry=registry,
)

findings_ai_enriched = Counter(
    'devarchai_findings_ai_enriched_total',
    'Findings enriched with AI',
    registry=registry,
)

findings_deduplicated = Counter(
    'devarchai_findings_deduplicated_total',
    'Duplicate findings removed',
    registry=registry,
)

findings_validation_fallbacks = Counter(
    'devarchai_findings_validation_fallbacks_total',
    'Findings that required validation fallback',
    registry=registry,
)

# ============================================================================
# CACHE METRICS
# ============================================================================

cache_hits_total = Counter(
    'devarchai_cache_hits_total',
    'Cache hits',
    ['cache_type'],  # ai_response, scan_result
    registry=registry,
)

cache_misses_total = Counter(
    'devarchai_cache_misses_total',
    'Cache misses',
    ['cache_type'],
    registry=registry,
)

cache_hit_rate = Gauge(
    'devarchai_cache_hit_rate',
    'Cache hit rate percentage',
    ['cache_type'],
    registry=registry,
)

# ============================================================================
# ERROR METRICS
# ============================================================================

errors_total = Counter(
    'devarchai_errors_total',
    'Total application errors',
    ['error_type', 'endpoint'],
    registry=registry,
)

# ============================================================================
# RAG METRICS
# ============================================================================

rag_retrievals_total = Counter(
    'devarchai_rag_retrievals_total',
    'RAG documentation retrievals',
    ['status'],  # success, failure
    registry=registry,
)

rag_documents_retrieved = Histogram(
    'devarchai_rag_documents_retrieved',
    'Number of documents retrieved per RAG call',
    buckets=[0, 1, 2, 3, 5, 10],
    registry=registry,
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def record_scan(status: str, technology: str, duration: float):
    """Record scan metrics."""
    scan_total.labels(status=status, technology=technology).inc()
    scan_duration_seconds.observe(duration)


def record_scan_start():
    """Increment active scan counter."""
    scan_active.inc()


def record_scan_end():
    """Decrement active scan counter."""
    scan_active.dec()


def record_ai_request(provider: str, status: str, duration: float):
    """Record AI request metrics."""
    ai_requests_total.labels(provider=provider, status=status).inc()
    ai_response_time_seconds.labels(provider=provider).observe(duration)


def record_finding(severity: str, category: str, ai_enriched: bool = False):
    """Record finding metrics."""
    findings_total.labels(severity=severity, category=category).inc()
    if ai_enriched:
        findings_ai_enriched.inc()


def record_deduplication(count: int):
    """Record deduplication metrics."""
    findings_deduplicated.inc(count)


def record_validation_fallback(count: int):
    """Record validation fallback metrics."""
    findings_validation_fallbacks.inc(count)


def record_cache_hit(cache_type: str):
    """Record cache hit."""
    cache_hits_total.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str):
    """Record cache miss."""
    cache_misses_total.labels(cache_type=cache_type).inc()


def record_error(error_type: str, endpoint: str):
    """Record error."""
    errors_total.labels(error_type=error_type, endpoint=endpoint).inc()


def record_rag_retrieval(status: str, doc_count: int):
    """Record RAG retrieval metrics."""
    rag_retrievals_total.labels(status=status).inc()
    rag_documents_retrieved.observe(doc_count)


# ============================================================================
# METRICS ENDPOINT
# ============================================================================

router = APIRouter(tags=["Metrics"])


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns all application metrics in Prometheus format.
    """
    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST,
    )


__all__ = [
    "router",
    "record_scan",
    "record_scan_start",
    "record_scan_end",
    "record_ai_request",
    "record_finding",
    "record_deduplication",
    "record_validation_fallback",
    "record_cache_hit",
    "record_cache_miss",
    "record_error",
    "record_rag_retrieval",
]
