"""Layered AI recommendation cache (L1 Redis + L2 PostgreSQL) and versioned cache keys.

Cache-first design for the AI recommendation pipeline:

- **L1** — Redis (``devarchai:ai:rec:{key}``), fastest path, TTL managed by Redis.
- **L2** — ``scan_ai_recommendations`` table, scan-independent persisted cache that
  survives Redis flush/restart. Rows are keyed by content (cache key), never by scan.

The cache key is deterministic and **versioned**: it hashes the rule, the
technology, a normalized fingerprint of the finding, a digest of the relevant
configuration (detected stack), and the context versions (RAG version, MCP
version, prompt version, model version). Bumping any version invalidates every
cached recommendation that depended on it — the old entries simply become
unreachable (different key).

Redis failures degrade to L2 / cache-miss (never an error).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

RECOMMENDATION_NAMESPACE = "devarchai:ai:rec:"
RECOMMENDATION_FORMAT_VERSION = "1"


def _sha256(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_text(value: str | None) -> str:
    """Collapse whitespace + lower for stable content fingerprinting."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.strip()).lower()


def normalize_finding(finding: Any) -> dict[str, str]:
    """Canonical, content-based representation of a finding for dedup."""
    return {
        "rule_id": str(getattr(finding, "rule_id", "") or ""),
        "severity": _enum_value(getattr(finding, "severity", "")),
        "category": _enum_value(getattr(finding, "category", "")),
        "description": normalize_text(getattr(finding, "description", "")),
        "recommendation": normalize_text(getattr(finding, "recommendation", "")),
        "file_path": _normalize_file_path(getattr(finding, "file_path", "")),
        "line_number": str(getattr(finding, "line_number", "") or ""),
    }


def finding_fingerprint(finding: Any) -> str:
    """Deterministic hash of a finding's normalized content."""
    return _sha256(json.dumps(normalize_finding(finding), sort_keys=True))[:32]


def config_digest(technologies: list[str] | None) -> str:
    """Deterministic digest of the relevant configuration (detected stack)."""
    if not technologies:
        return ""
    return _sha256(json.dumps(sorted({t.strip().lower() for t in technologies if t})))[:16]


def _enum_value(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _normalize_file_path(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.replace("\\", "/")
    if "/tmp/devarchai/" in normalized:
        normalized = normalized.split("/tmp/devarchai/", 1)[1]
        if "/" in normalized:
            normalized = normalized.split("/", 1)[1]
    return normalize_text(normalized)


def effective_model_version() -> str:
    """Model component for the cache key. Overridable via settings."""
    explicit = getattr(settings, "AI_RECOMMENDATION_MODEL_VERSION", None)
    if explicit:
        return explicit
    provider = getattr(settings, "LLM_PROVIDER", "mock")
    model = getattr(settings, "LLM_MODEL", "")
    return f"{provider}:{model}".strip(":")


def context_versions() -> dict[str, str]:
    """Versions of every input that can change a recommendation's meaning."""
    return {
        "rag": str(getattr(settings, "RAG_VERSION", "1.0.0")),
        "mcp": str(getattr(settings, "MCP_CONTEXT_VERSION", "1.0.0")),
        "prompt": str(getattr(settings, "AI_RECOMMENDATION_PROMPT_VERSION", "1.0.0")),
        "model": effective_model_version(),
    }


def recommendation_cache_key(
    rule_id: str,
    technology: str | None,
    fingerprint: str,
    config_digest_value: str,
    versions: dict[str, str] | None = None,
) -> str:
    """Deterministic, versioned cache key for a recommendation."""
    raw = json.dumps(
        {
            "f": RECOMMENDATION_FORMAT_VERSION,
            "rule": (rule_id or "").strip().lower(),
            "tech": normalize_text(technology),
            "fp": fingerprint,
            "cfg": config_digest_value,
            "v": versions or context_versions(),
        },
        sort_keys=True,
    )
    return _sha256(raw)[:40]


def _ttl_for_source(source: str) -> int:
    if source in ("mcp", "live"):
        return int(settings.AI_RECOMMENDATION_LIVE_TTL_SECONDS)
    return int(settings.AI_RECOMMENDATION_CACHE_TTL_SECONDS)


@dataclass
class RecommendationEntry:
    """A cached recommendation plus its provenance."""

    cache_key: str
    payload: dict[str, Any]
    source: str = "llm"  # llm | mcp | rag | fallback
    ai_generated: bool = False
    rag_version: str = ""
    mcp_version: str = ""
    prompt_version: str = ""
    model_version: str = ""
    ttl_seconds: int = 0
    origin_finding_id: str | None = None
    versions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cache_key": self.cache_key,
            "payload": self.payload,
            "source": self.source,
            "ai_generated": self.ai_generated,
            "rag_version": self.rag_version,
            "mcp_version": self.mcp_version,
            "prompt_version": self.prompt_version,
            "model_version": self.model_version,
            "ttl_seconds": self.ttl_seconds,
        }

    @classmethod
    def from_dict(cls, cache_key: str, raw: dict[str, Any]) -> "RecommendationEntry":
        return cls(
            cache_key=cache_key,
            payload=raw.get("payload", {}),
            source=raw.get("source", "llm"),
            ai_generated=bool(raw.get("ai_generated", False)),
            rag_version=str(raw.get("rag_version", "")),
            mcp_version=str(raw.get("mcp_version", "")),
            prompt_version=str(raw.get("prompt_version", "")),
            model_version=str(raw.get("model_version", "")),
            ttl_seconds=int(raw.get("ttl_seconds", 0) or 0),
        )


class RecommendationCache:
    """Layered cache: Redis (L1) + ``scan_ai_recommendations`` (L2)."""

    def __init__(
        self,
        redis_client: Any | None = None,
        session_factory: Any | None = None,
        ttl_seconds: int | None = None,
        live_ttl_seconds: int | None = None,
    ) -> None:
        self._redis_client = redis_client
        self._session_factory = session_factory
        self._ttl_seconds = ttl_seconds or _ttl_for_source("llm")
        self._live_ttl_seconds = live_ttl_seconds or _ttl_for_source("mcp")

    def ttl_for(self, source: str) -> int:
        if source in ("mcp", "live"):
            return self._live_ttl_seconds
        return self._ttl_seconds

    async def _redis(self) -> Any | None:
        if self._redis_client is not None:
            return self._redis_client
        try:
            from app.services.cache import get_cache
            return await get_cache()
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("RECOMMENDATION_CACHE_REDIS_UNAVAILABLE", error=str(exc))
            return None

    def _redis_key(self, cache_key: str) -> str:
        return f"{RECOMMENDATION_NAMESPACE}{cache_key}"

    async def get(self, cache_key: str) -> RecommendationEntry | None:
        """Return the cached recommendation, or None on miss (L1 then L2)."""
        redis = await self._redis()
        if redis is not None:
            try:
                raw = await redis.get(self._redis_key(cache_key))
                if raw is not None:
                    logger.info(
                        "AI_RECOMMENDATION_CACHE_HIT",
                        layer="redis",
                        source="cache",
                    )
                    return RecommendationEntry.from_dict(cache_key, raw)
            except Exception as exc:
                logger.debug("AI_RECOMMENDATION_CACHE_L1_ERROR", error=str(exc))

        entry = await self._get_l2(cache_key)
        if entry is not None:
            logger.info(
                "AI_RECOMMENDATION_CACHE_HIT",
                layer="postgres",
                source=entry.source,
            )
            # Re-populate L1 so subsequent scans hit Redis.
            if redis is not None:
                await self._set_l1(redis, entry)
            return entry
        return None

    async def set(self, entry: RecommendationEntry) -> bool:
        """Persist a recommendation to L2 and populate L1."""
        await self._set_l2(entry)
        redis = await self._redis()
        if redis is not None:
            await self._set_l1(redis, entry)
        return True

    async def delete(self, cache_key: str) -> None:
        """Remove a recommendation from both layers (used for invalidation)."""
        redis = await self._redis()
        if redis is not None:
            try:
                await redis.delete(self._redis_key(cache_key))
            except Exception:
                pass
        await self._delete_l2(cache_key)

    # ------------------------------------------------------------------
    # L1 (Redis)
    # ------------------------------------------------------------------

    async def _set_l1(self, redis: Any, entry: RecommendationEntry) -> None:
        try:
            await redis.set(
                self._redis_key(entry.cache_key),
                entry.to_dict(),
                timedelta(seconds=entry.ttl_seconds or self.ttl_for(entry.source)),
            )
        except Exception as exc:
            logger.debug("AI_RECOMMENDATION_CACHE_L1_SET_ERROR", error=str(exc))

    # ------------------------------------------------------------------
    # L2 (PostgreSQL)
    # ------------------------------------------------------------------

    async def _session(self) -> Any:
        if self._session_factory is not None:
            return self._session_factory()
        from app.db.session import get_session_factory
        return get_session_factory()()

    async def _get_l2(self, cache_key: str) -> RecommendationEntry | None:
        try:
            from sqlalchemy import select
            from app.models.scan_ai_recommendation import ScanAIRecommendation

            now = datetime.now(UTC)
            async with await self._session() as session:
                row = (
                    await session.execute(
                        select(ScanAIRecommendation).where(
                            ScanAIRecommendation.cache_key == cache_key,
                            ScanAIRecommendation.expires_at > now,
                        )
                    )
                ).scalar_one_or_none()
            if row is None:
                return None
            return RecommendationEntry(
                cache_key=cache_key,
                payload=dict(row.payload or {}),
                source=row.source,
                ai_generated=bool(row.ai_generated),
                rag_version=row.rag_version,
                mcp_version=row.mcp_version,
                prompt_version=row.prompt_version,
                model_version=row.model_version,
                ttl_seconds=int(row.ttl_seconds or 0),
            )
        except Exception as exc:
            logger.debug("AI_RECOMMENDATION_CACHE_L2_GET_ERROR", error=str(exc))
            return None

    async def _set_l2(self, entry: RecommendationEntry) -> None:
        try:
            from sqlalchemy import select
            from app.models.scan_ai_recommendation import ScanAIRecommendation

            async with await self._session() as session:
                row = (
                    await session.execute(
                        select(ScanAIRecommendation).where(
                            ScanAIRecommendation.cache_key == entry.cache_key
                        )
                    )
                ).scalar_one_or_none()
                if row is None:
                    row = ScanAIRecommendation(
                        cache_key=entry.cache_key,
                        finding_fingerprint=entry.payload.get("finding_fingerprint", "") or "",
                    )
                    session.add(row)

                row.finding_fingerprint = entry.payload.get("finding_fingerprint", "") or row.finding_fingerprint
                row.rule_id = entry.payload.get("rule_id", "") or row.rule_id
                row.technology = entry.payload.get("technology") or row.technology
                row.rag_version = entry.rag_version or row.rag_version
                row.mcp_version = entry.mcp_version or row.mcp_version
                row.prompt_version = entry.prompt_version or row.prompt_version
                row.model_version = entry.model_version or row.model_version
                row.payload = entry.payload
                row.source = entry.source
                row.ai_generated = entry.ai_generated
                row.ttl_seconds = entry.ttl_seconds or self.ttl_for(entry.source)
                row.expires_at = datetime.now(UTC) + timedelta(
                    seconds=entry.ttl_seconds or self.ttl_for(entry.source)
                )
                row.origin_finding_id = entry.origin_finding_id
                await session.commit()
        except Exception as exc:
            logger.debug("AI_RECOMMENDATION_CACHE_L2_SET_ERROR", error=str(exc))

    async def _delete_l2(self, cache_key: str) -> None:
        try:
            from sqlalchemy import delete
            from app.models.scan_ai_recommendation import ScanAIRecommendation

            async with await self._session() as session:
                await session.execute(
                    delete(ScanAIRecommendation).where(
                        ScanAIRecommendation.cache_key == cache_key
                    )
                )
                await session.commit()
        except Exception as exc:
            logger.debug("AI_RECOMMENDATION_CACHE_L2_DELETE_ERROR", error=str(exc))


# Singleton
_recommendation_cache: RecommendationCache | None = None


def get_recommendation_cache() -> RecommendationCache:
    """Get the global recommendation cache singleton."""
    global _recommendation_cache
    if _recommendation_cache is None:
        _recommendation_cache = RecommendationCache()
    return _recommendation_cache
