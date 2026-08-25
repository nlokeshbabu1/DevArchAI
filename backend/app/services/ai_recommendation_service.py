"""AI Recommendation Service — async, scan-independent recommendation pipeline.

Orchestrates the pipeline for a completed scan:

1. Idempotency guard: skip scans already ``processing`` / ``completed``.
2. Load findings (bounded by ``AI_RECOMMENDATIONS_MAX_PER_SCAN``).
3. Deduplicate by the deterministic, versioned cache key — N identical
   findings share one context build and one LLM call.
4. Cache-first: L1 Redis + L2 PostgreSQL lookup before any context work.
5. On miss, assemble grounded context (RAG → optional MCP) and generate the
   recommendation via the context engine (LLM with static fallback).
6. Persist to the recommendation cache, apply to findings + suggestions, and
   stream progress over WebSocket.

The scan's ``status`` is never touched: the scanner already committed
``COMPLETED`` before this job is enqueued. AI failures only affect
``scan.ai_status``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import UUID

import structlog

from app.config import settings
from app.services.ai_recommendation_cache import (
    RecommendationCache,
    RecommendationEntry,
    config_digest,
    context_versions,
    finding_fingerprint,
    recommendation_cache_key,
)
from app.ai.context_engine import AIContextEngine, AIRecommendation

logger = structlog.get_logger(__name__)


@dataclass
class AIRecommendationRunResult:
    """Summary of one recommendation pipeline run."""

    findings_processed: int
    findings_updated: int
    cache_hits: int
    llm_calls: int
    rag_lookups: int
    mcp_required: int
    suggestions_upserted: int
    groups: int


class AIRecommendationService:
    """Runs the recommendation pipeline for one scan."""

    def __init__(
        self,
        session: Any,
        cache: RecommendationCache | None = None,
        context_engine: AIContextEngine | None = None,
        snippet_loader: Callable[[Any, Any], str] | None = None,
        max_per_scan: int | None = None,
    ) -> None:
        self.session = session
        self.cache = cache or _default_cache()
        self.context_engine = context_engine or AIContextEngine()
        self.snippet_loader = snippet_loader or _default_snippet_loader()
        self.max_per_scan = max_per_scan or int(
            getattr(settings, "AI_RECOMMENDATIONS_MAX_PER_SCAN", None) or 50
        )

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    async def process_scan(self, scan_id: UUID | str) -> AIRecommendationRunResult:
        from sqlalchemy.orm import selectinload

        from app.models.scan import Scan

        scan_uuid = scan_id if isinstance(scan_id, UUID) else UUID(str(scan_id))
        from sqlalchemy import select
        scan = (
            await self.session.execute(
                select(Scan)
                .where(Scan.id == scan_uuid)
                .options(selectinload(Scan.findings))
            )
        ).scalar_one_or_none()
        if scan is None:
            raise ValueError(f"Scan not found: {scan_id}")

        if scan.ai_status == "completed":
            logger.info(
                "AI_RECOMMENDATION_SKIP_ALREADY_DONE",
                scan_id=str(scan_uuid),
                ai_status=scan.ai_status,
            )
            return AIRecommendationRunResult(
                findings_processed=0,
                findings_updated=0,
                cache_hits=0,
                llm_calls=0,
                rag_lookups=0,
                mcp_required=0,
                suggestions_upserted=0,
                groups=0,
            )

        scan.ai_status = "processing"
        scan.ai_error_message = None
        scan.ai_completed_at = None
        await self.session.commit()
        findings_total = len(getattr(scan, "findings", None) or [])
        await self._broadcast_started(str(scan_uuid), findings_total=findings_total)

        try:
            result = await self._run_pipeline(scan)
        except Exception as exc:
            await self.session.rollback()
            scan = await self.session.get(Scan, scan_uuid)
            if scan is not None:
                scan.ai_status = "failed"
                scan.ai_error_message = str(exc)[:1000]
                await self.session.commit()
            logger.exception(
                "AI_RECOMMENDATION_PIPELINE_FAILED",
                scan_id=str(scan_uuid),
                error=str(exc),
            )
            await self._broadcast_failed(str(scan_uuid), str(exc))
            raise

        scan = await self.session.get(Scan, scan_uuid)
        if scan is not None:
            scan.ai_status = "completed"
            scan.ai_completed_at = datetime.now(UTC)
            scan.ai_error_message = None
            await self.session.commit()
        await self._broadcast_completed(str(scan_uuid), result)

        logger.info(
            "AI_RECOMMENDATION_PIPELINE_COMPLETED",
            scan_id=str(scan_uuid),
            findings_processed=result.findings_processed,
            findings_updated=result.findings_updated,
            cache_hits=result.cache_hits,
            llm_calls=result.llm_calls,
            rag_lookups=result.rag_lookups,
            mcp_required=result.mcp_required,
            suggestions_upserted=result.suggestions_upserted,
            groups=result.groups,
        )
        return result

    async def _run_pipeline(self, scan: Any) -> AIRecommendationRunResult:
        from app.models.finding import Finding
        from sqlalchemy import select

        scan_uuid = scan.id
        findings = (
            (
                await self.session.execute(
                    select(Finding)
                    .where(Finding.scan_id == scan_uuid)
                    .order_by(Finding.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        if not findings:
            return AIRecommendationRunResult(0, 0, 0, 0, 0, 0, 0, 0)

        findings = findings[: self.max_per_scan]
        total = len(findings)

        config_digest_value = config_digest(
            (scan.detected_stack or []) if isinstance(scan.detected_stack, list) else None
        )
        versions = context_versions()

        # Dedup by deterministic cache key.
        groups: dict[str, list[Any]] = {}
        for finding in findings:
            tech = self.context_engine.technology_for_finding(finding)
            fingerprint = finding_fingerprint(finding)
            rule_id = str(getattr(finding, "rule_id", "") or "")
            key = recommendation_cache_key(rule_id, tech, fingerprint, config_digest_value, versions)
            groups.setdefault(key, []).append(finding)

        cache_hits = 0
        llm_calls = 0
        rag_lookups = 0
        mcp_required = 0
        findings_updated = 0
        processed = 0
        suggestions_upserted = 0

        for index, (key, group) in enumerate(groups.items()):
            representative = group[0]
            fingerprint = finding_fingerprint(representative)
            rule_id = str(getattr(representative, "rule_id", "") or "")
            technology = self.context_engine.technology_for_finding(representative)

            logger.info(
                "AI_PIPELINE_FINDING_START",
                scan_id=str(scan_uuid),
                rule_id=rule_id,
                technology=technology,
                group_index=index + 1,
                groups_total=len(groups),
            )

            entry = await self.cache.get(key)
            if entry is not None:
                cache_hits += 1
                recommendation = self._recommendation_from_entry(entry, representative, fingerprint)
                logger.info(
                    "AI_PIPELINE_CACHE_HIT",
                    scan_id=str(scan_uuid),
                    rule_id=rule_id,
                    layer=getattr(entry, "source", "unknown"),
                )
                await self._broadcast_cache_hit(str(scan_uuid), rule_id, entry)
            else:
                # RAG retrieval
                context = await self.context_engine.build_context(
                    representative,
                    file_snippet=self.snippet_loader(scan, representative),
                )
                if context.rule_knowledge is not None:
                    rag_lookups += 1
                    docs_found = len(getattr(context.rule_knowledge, "documents", []) or [])
                    logger.info(
                        "AI_PIPELINE_RAG_COMPLETED",
                        scan_id=str(scan_uuid),
                        rule_id=rule_id,
                        documents_found=docs_found,
                        method=getattr(context.rule_knowledge, "method", "unknown"),
                    )
                    await self._broadcast_rag_completed(
                        str(scan_uuid), rule_id, context
                    )

                # MCP decision + retrieval
                if context.mcp_results:
                    mcp_required += 1
                    mcp_statuses = [getattr(r, "status", "unknown") for r in context.mcp_results]
                    logger.info(
                        "AI_PIPELINE_MCP_COMPLETED",
                        scan_id=str(scan_uuid),
                        rule_id=rule_id,
                        technology=technology,
                        results_count=len(context.mcp_results),
                        statuses=mcp_statuses,
                    )
                    await self._broadcast_mcp_completed(
                        str(scan_uuid), rule_id, technology, context
                    )

                # LLM generation
                await self._broadcast_llm_started(str(scan_uuid), rule_id, technology)
                recommendation = await self.context_engine.generate_recommendation(
                    representative, context, fingerprint
                )
                if recommendation.ai_generated:
                    llm_calls += 1
                await self._broadcast_llm_completed(
                    str(scan_uuid), rule_id, recommendation
                )

                await self._persist_recommendation(
                    key, recommendation, representative, scan_uuid, versions, context
                )
                # Re-read from cache so the entry reflects the stored payload.
                cached = await self.cache.get(key)
                entry = cached if cached is not None else entry

            updated = await self._apply_recommendation(group, recommendation, scan_uuid)
            findings_updated += updated
            suggestions_upserted += updated
            processed += len(group)
            await self.session.commit()

            await self._broadcast_finding_completed(str(scan_uuid), index + 1, len(groups))
            self._record_metrics(recommendation, entry, group, index, len(groups))

        return AIRecommendationRunResult(
            findings_processed=processed,
            findings_updated=findings_updated,
            cache_hits=cache_hits,
            llm_calls=llm_calls,
            rag_lookups=rag_lookups,
            mcp_required=mcp_required,
            suggestions_upserted=suggestions_upserted,
            groups=len(groups),
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def _persist_recommendation(
        self,
        key: str,
        recommendation: AIRecommendation,
        finding: Any,
        scan_uuid: UUID,
        versions: dict[str, str],
        context: Any,
    ) -> None:
        payload = recommendation.to_dict()
        payload["finding_fingerprint"] = payload.get("finding_fingerprint") or finding_fingerprint(finding)
        payload["rule_id"] = payload.get("rule_id") or str(getattr(finding, "rule_id", "") or "")
        payload["technology"] = payload.get("technology") or recommendation.technology
        entry = RecommendationEntry(
            cache_key=key,
            payload=payload,
            source=recommendation.source,
            ai_generated=recommendation.ai_generated,
            rag_version=versions.get("rag", "") or context.rag_version,
            mcp_version=versions.get("mcp", "") or context.mcp_version,
            prompt_version=versions.get("prompt", ""),
            model_version=versions.get("model", ""),
            ttl_seconds=self.cache.ttl_for(recommendation.source),
            origin_finding_id=str(finding.id),
        )
        await self.cache.set(entry)

    def _recommendation_from_entry(
        self,
        entry: RecommendationEntry,
        finding: Any,
        fingerprint: str,
    ) -> AIRecommendation:
        p = entry.payload or {}
        best_practices = p.get("best_practices") or []
        if isinstance(best_practices, str):
            best_practices = [best_practices]
        return AIRecommendation(
            finding_fingerprint=p.get("finding_fingerprint") or fingerprint,
            rule_id=p.get("rule_id") or str(getattr(finding, "rule_id", "") or ""),
            technology=p.get("technology"),
            summary=str(p.get("summary", "") or ""),
            risk=str(p.get("risk", "") or ""),
            impact=str(p.get("impact", "") or ""),
            ai_explanation=str(p.get("ai_explanation", "") or ""),
            fix_code=str(p.get("fix_code", "") or ""),
            fix_example=str(p.get("fix_example", "") or ""),
            full_example=str(p.get("full_example", "") or ""),
            best_practices=[str(item) for item in best_practices[:3]],
            confidence=_coerce_confidence(p.get("confidence", 0.55)),
            documentation_url=str(p.get("documentation_url", "") or ""),
            ai_generated=bool(entry.ai_generated),
            source=entry.source,
        )

    async def _apply_recommendation(
        self,
        findings: list[Any],
        recommendation: AIRecommendation,
        scan_uuid: UUID,
    ) -> int:
        """Write the recommendation onto findings + AISuggestion rows."""
        from app.models.ai_suggestion import AISuggestion, FixType, SuggestionStatus
        from sqlalchemy import select

        updated = 0
        for finding in findings:
            finding.summary = recommendation.summary or finding.summary
            finding.risk = recommendation.risk or finding.risk
            finding.impact = recommendation.impact or finding.impact
            finding.ai_explanation = recommendation.ai_explanation or finding.ai_explanation
            finding.fix_code = recommendation.fix_code or finding.fix_code
            finding.fix_example = recommendation.fix_example or finding.fix_example
            finding.full_example = recommendation.full_example or finding.full_example
            finding.best_practices = _serialize_json(recommendation.best_practices) or finding.best_practices
            finding.documentation_url = recommendation.documentation_url or finding.documentation_url
            finding.confidence = recommendation.confidence
            finding.confidence_score = recommendation.confidence
            finding.ai_generated = recommendation.ai_generated
            self.session.add(finding)
            updated += 1

            existing = (
                await self.session.execute(
                    select(AISuggestion).where(AISuggestion.finding_id == finding.id)
                )
            ).scalar_one_or_none()
            if existing is None:
                suggestion = AISuggestion(
                    finding_id=finding.id,
                    scan_id=scan_uuid,
                    title=recommendation.summary or finding.rule_name or f"Fix {finding.rule_id}",
                    description=recommendation.ai_explanation or finding.description or "",
                    severity=_enum_value(finding.severity),
                    confidence=recommendation.confidence,
                    category=_enum_value(finding.category),
                    fix_type=_determine_fix_type(finding.file_path),
                    file_path=finding.file_path or "",
                    line_number=finding.line_number,
                    fix_code=recommendation.fix_code or recommendation.fix_example or recommendation.full_example,
                    auto_fix_available=bool(recommendation.fix_code or recommendation.fix_example),
                    status=SuggestionStatus.OPEN,
                    additional_data=_serialize_json(
                        {
                            "rule_id": finding.rule_id,
                            "recommendation": finding.recommendation,
                            "best_practices": recommendation.best_practices,
                            "ai_generated": recommendation.ai_generated,
                            "cache_key_source": recommendation.source,
                        }
                    ),
                )
                self.session.add(suggestion)
        return updated

    # ------------------------------------------------------------------
    # WebSocket / metrics
    # ------------------------------------------------------------------

    async def _broadcast_started(self, scan_id: str, findings_total: int = 0) -> None:
        try:
            from app.websockets.scan_progress import scan_progress_manager
            await scan_progress_manager.broadcast_ai_started(
                scan_id,
                "Generating AI remediation suggestions",
                findings_total=findings_total,
            )
            await scan_progress_manager.broadcast_ai_analysis_started(
                scan_id, findings_total=findings_total
            )
            await scan_progress_manager.broadcast_ai_progress(
                scan_id, phase="building_context", message_text="Building AI recommendations…", progress=0
            )
        except Exception as exc:
            logger.debug("AI_RECOMMENDATION_WS_STARTED_ERROR", error=str(exc))

    async def _broadcast_finding_completed(self, scan_id: str, index: int, total: int) -> None:
        try:
            from app.websockets.scan_progress import scan_progress_manager
            await scan_progress_manager.broadcast_ai_finding_completed(scan_id, index, total)
            await scan_progress_manager.broadcast_ai_progress(
                scan_id,
                phase="generating",
                message_text=f"AI recommendation {index} of {total}",
                progress=int(index / max(total, 1) * 100),
                findings_processed=index,
                findings_total=total,
            )
        except Exception as exc:
            logger.debug("AI_RECOMMENDATION_WS_FINDING_ERROR", error=str(exc))

    async def _broadcast_completed(
        self, scan_id: str, result: AIRecommendationRunResult
    ) -> None:
        try:
            from app.websockets.scan_progress import scan_progress_manager
            await scan_progress_manager.broadcast_ai_analysis_completed(
                scan_id,
                {
                    "findings_processed": result.findings_processed,
                    "findings_updated": result.findings_updated,
                    "cache_hits": result.cache_hits,
                    "llm_calls": result.llm_calls,
                    "groups": result.groups,
                },
            )
            await scan_progress_manager.broadcast_ai_completed(
                scan_id, status="completed", suggestions_count=result.findings_updated
            )
        except Exception as exc:
            logger.debug("AI_RECOMMENDATION_WS_COMPLETED_ERROR", error=str(exc))

    async def _broadcast_failed(self, scan_id: str, error: str) -> None:
        try:
            from app.websockets.scan_progress import scan_progress_manager
            await scan_progress_manager.broadcast_ai_analysis_failed(scan_id, error)
        except Exception as exc:
            logger.debug("AI_RECOMMENDATION_WS_FAILED_ERROR", error=str(exc))

    async def _broadcast_cache_hit(
        self, scan_id: str, rule_id: str, entry: Any
    ) -> None:
        try:
            from app.websockets.scan_progress import scan_progress_manager
            layer = getattr(entry, "source", "cache")
            await scan_progress_manager.broadcast_ai_cache_hit(scan_id, rule_id, layer)
        except Exception as exc:
            logger.debug("AI_RECOMMENDATION_WS_CACHE_HIT_ERROR", error=str(exc))

    async def _broadcast_rag_completed(
        self, scan_id: str, rule_id: str, context: Any
    ) -> None:
        try:
            from app.websockets.scan_progress import scan_progress_manager
            rk = context.rule_knowledge
            docs_found = len(getattr(rk, "documents", []) or []) if rk else 0
            method = getattr(rk, "method", "unknown") if rk else "unknown"
            await scan_progress_manager.broadcast_ai_rag_completed(
                scan_id, rule_id, docs_found, method
            )
        except Exception as exc:
            logger.debug("AI_RECOMMENDATION_WS_RAG_ERROR", error=str(exc))

    async def _broadcast_mcp_completed(
        self, scan_id: str, rule_id: str, technology: str | None, context: Any
    ) -> None:
        try:
            from app.websockets.scan_progress import scan_progress_manager
            for mcp_result in context.mcp_results:
                status = getattr(mcp_result, "status", "unknown") or "unknown"
                provider = getattr(mcp_result, "provider", "") or ""
                await scan_progress_manager.broadcast_ai_mcp_completed(
                    scan_id, rule_id, technology or "unknown", status, provider
                )
        except Exception as exc:
            logger.debug("AI_RECOMMENDATION_WS_MCP_ERROR", error=str(exc))

    async def _broadcast_llm_started(
        self, scan_id: str, rule_id: str, technology: str | None
    ) -> None:
        try:
            from app.websockets.scan_progress import scan_progress_manager
            await scan_progress_manager.broadcast_ai_llm_started(
                scan_id, rule_id, technology
            )
        except Exception as exc:
            logger.debug("AI_RECOMMENDATION_WS_LLM_STARTED_ERROR", error=str(exc))

    async def _broadcast_llm_completed(
        self, scan_id: str, rule_id: str, recommendation: Any
    ) -> None:
        try:
            from app.websockets.scan_progress import scan_progress_manager
            await scan_progress_manager.broadcast_ai_llm_completed(
                scan_id, rule_id, recommendation.ai_generated
            )
        except Exception as exc:
            logger.debug("AI_RECOMMENDATION_WS_LLM_COMPLETED_ERROR", error=str(exc))

    def _record_metrics(
        self,
        recommendation: AIRecommendation,
        entry: RecommendationEntry | None,
        group: list[Any],
        index: int,
        total: int,
    ) -> None:
        try:
            from app.services.metrics import record_cache_hit, record_cache_miss
            if entry is not None:
                record_cache_hit("ai_recommendation")
            else:
                record_cache_miss("ai_recommendation")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Module-level helpers / defaults
# ---------------------------------------------------------------------------


def _default_cache() -> RecommendationCache:
    from app.services.ai_recommendation_cache import get_recommendation_cache
    return get_recommendation_cache()


def _default_snippet_loader() -> Callable[[Any, Any], str]:
    from app.utils.repository_scanner import RepositoryScanner
    from app.services.ai_recommendation_snippets import RepoFileSnippetLoader
    return RepoFileSnippetLoader(repo_scanner=RepositoryScanner()).snippet_for


def _coerce_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = 0.55
    return max(0.0, min(confidence, 1.0))


def _serialize_json(value: Any) -> str | None:
    import json
    if not value:
        return None
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return None


def _enum_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value.value) if hasattr(value, "value") else str(value)


def _determine_fix_type(file_path: str | None) -> Any:
    from app.models.ai_suggestion import FixType
    path_lower = (file_path or "").lower()
    if ".tf" in path_lower or "terraform" in path_lower:
        return FixType.TERRAFORM
    if "dockerfile" in path_lower or "docker" in path_lower:
        return FixType.DOCKERFILE
    if "kubernetes" in path_lower or "k8s" in path_lower or path_lower.endswith((".yaml", ".yml")):
        return FixType.KUBERNETES
    if ".github" in path_lower or "jenkins" in path_lower or "gitlab-ci" in path_lower or "pipeline" in path_lower:
        return FixType.CI_CD
    return FixType.GENERAL


async def run_ai_recommendations_for_scan(
    scan_id: UUID | str,
    session: Any | None = None,
    service: AIRecommendationService | None = None,
) -> AIRecommendationRunResult:
    """Entry point: run the recommendation pipeline for a scan."""
    owns_session = session is None
    if owns_session:
        from app.db.session import get_session_factory
        session = get_session_factory()()
    try:
        svc = service or AIRecommendationService(session=session)
        return await svc.process_scan(scan_id)
    finally:
        if owns_session:
            await session.close()


def enqueue_ai_analysis_for_scan(scan_id: UUID | str) -> None:
    """Enqueue AI analysis; default is an in-process thread (no Celery worker required).

    Never blocks or raises: the scanner already committed ``COMPLETED`` before
    this is called, so AI analysis is strictly async and scan-independent.
    """
    from app.config import settings

    scan_id_str = str(scan_id)
    use_celery = bool(getattr(settings, "CELERY_AI_TASKS_ENABLED", False))

    if use_celery:
        try:
            from app.workers.tasks.ai_recommendations import enqueue_ai_analysis

            enqueue_ai_analysis.delay(scan_id_str)
            logger.info("AI_RECOMMENDATION_ENQUEUED", scan_id=scan_id_str, transport="celery")
            return
        except Exception as exc:
            logger.warning(
                "AI_RECOMMENDATION_CELERY_UNAVAILABLE",
                scan_id=scan_id_str,
                error=str(exc)[:300],
            )

    def _fallback_runner() -> None:
        try:
            asyncio.run(run_ai_recommendations_for_scan(scan_id_str))
        except Exception as run_exc:  # pragma: no cover - defensive
            logger.exception(
                "AI_RECOMMENDATION_FALLBACK_FAILED",
                scan_id=scan_id_str,
                error=str(run_exc),
            )

    import threading

    thread = threading.Thread(
        target=_fallback_runner,
        name=f"ai-recommendations-{scan_id_str[:8]}",
        daemon=True,
    )
    thread.start()
    logger.info("AI_RECOMMENDATION_ENQUEUED", scan_id=scan_id_str, transport="thread")
