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
import uuid as uuid_mod

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
from app.services.ai_eligibility import filter_ai_eligible_findings, finding_severity_value
from app.services.ai_job_service import (
    aggregate_scan_ai_status,
    ensure_jobs_for_scan,
    set_job_status,
)
from app.ai.context_engine import AIContextEngine, AIRecommendation
from app.models.finding_ai_job import FindingAIJob, FindingAIJobStatus
from app.services.ai_source_provenance import (
    collect_sources,
    documentation_status,
    normalize_sources,
)

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
        session_factory: Any | None = None,
    ) -> None:
        self.session = session
        self.session_factory = session_factory
        self.cache = cache or _default_cache()
        if context_engine is None:
            from app.rag.service import create_rag_service

            context_engine = AIContextEngine(
                rag_service=create_rag_service(session_factory),
            )
        self.context_engine = context_engine
        loader = snippet_loader
        if loader is None:
            from app.services.ai_recommendation_snippets import RepoFileSnippetLoader
            self._file_loader: Any | None = RepoFileSnippetLoader(repo_scanner=_default_repo_scanner())
            self.snippet_loader = self._file_loader.snippet_for
        elif hasattr(loader, "snippet_for"):
            self._file_loader = loader
            self.snippet_loader = loader.snippet_for
        else:
            self._file_loader = None
            self.snippet_loader = loader
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
        from sqlalchemy import select

        from app.models.finding import Finding

        raw_findings = list(getattr(scan, "findings", None) or [])
        if not raw_findings:
            raw_findings = list(
                (await self.session.execute(select(Finding).where(Finding.scan_id == scan_uuid)))
                .scalars()
                .all()
            )
        eligible_findings = filter_ai_eligible_findings(raw_findings)
        info_excluded = sum(1 for f in raw_findings if finding_severity_value(f) == "info")
        jobs = await ensure_jobs_for_scan(
            self.session, scan_uuid, max_per_scan=self.max_per_scan, context_engine=self.context_engine
        )
        await self._broadcast_started(
            str(scan_uuid),
            findings_total=len(jobs),
            total_findings=len(raw_findings),
            info_excluded=info_excluded,
        )
        if not jobs:
            scan.ai_status = "completed"
            scan.ai_completed_at = datetime.now(UTC)
            await self.session.commit()
            return AIRecommendationRunResult(0, 0, 0, 0, 0, 0, 0, 0)

        try:
            result = await self._run_pipeline(scan, jobs)
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
            await aggregate_scan_ai_status(self.session, scan_uuid)
            scan = await self.session.get(Scan, scan_uuid)
            if scan is not None and scan.ai_status not in ("failed",):
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

    async def _try_claim_job(
        self,
        job_id: UUID,
        *,
        celery_task_id: str | None = None,
    ) -> bool:
        """Atomically claim a queued job (prevents duplicate Celery/thread workers)."""
        from sqlalchemy import update

        now = datetime.now(UTC)
        result = await self.session.execute(
            update(FindingAIJob)
            .where(
                FindingAIJob.id == job_id,
                FindingAIJob.status.in_(
                    [
                        FindingAIJobStatus.QUEUED.value,
                        FindingAIJobStatus.NOT_STARTED.value,
                        FindingAIJobStatus.RETRYING.value,
                    ]
                ),
            )
            .values(
                status=FindingAIJobStatus.CHECKING_CACHE.value,
                started_at=now,
                updated_at=now,
                celery_task_id=celery_task_id,
            )
        )
        if result.rowcount:
            await self.session.commit()
            return True
        await self.session.rollback()
        return False

    async def _run_pipeline(
        self, scan: Any, jobs: list[FindingAIJob]
    ) -> AIRecommendationRunResult:
        scan_uuid = scan.id
        cache_hits = 0
        llm_calls = 0
        rag_lookups = 0
        mcp_required = 0
        findings_updated = 0
        processed = 0

        for index, job in enumerate(jobs):
            group_result = await self.process_job(job.id, group_index=index + 1, groups_total=len(jobs))
            cache_hits += group_result.get("cache_hits", 0)
            llm_calls += group_result.get("llm_calls", 0)
            rag_lookups += group_result.get("rag_lookups", 0)
            mcp_required += group_result.get("mcp_required", 0)
            findings_updated += group_result.get("findings_updated", 0)
            processed += group_result.get("findings_processed", 0)

        return AIRecommendationRunResult(
            findings_processed=processed,
            findings_updated=findings_updated,
            cache_hits=cache_hits,
            llm_calls=llm_calls,
            rag_lookups=rag_lookups,
            mcp_required=mcp_required,
            suggestions_upserted=findings_updated,
            groups=len(jobs),
        )

    async def process_job(
        self,
        job_id: UUID | str,
        *,
        group_index: int = 1,
        groups_total: int = 1,
        celery_task_id: str | None = None,
    ) -> dict[str, int]:
        """Process one deduplicated finding-group AI job (idempotent)."""
        from app.models.finding import Finding
        from app.models.scan import Scan
        from sqlalchemy import select

        job_uuid = job_id if isinstance(job_id, UUID) else UUID(str(job_id))
        job = await self.session.get(FindingAIJob, job_uuid)
        if job is None:
            raise ValueError(f"AI job not found: {job_id}")
        if job.is_terminal:
            return {
                "cache_hits": 0,
                "llm_calls": 0,
                "rag_lookups": 0,
                "mcp_required": 0,
                "findings_updated": 0,
                "findings_processed": len(job.finding_ids or []),
            }

        claimed = await self._try_claim_job(job_uuid, celery_task_id=celery_task_id)
        if not claimed:
            refreshed = await self.session.get(FindingAIJob, job_uuid)
            return {
                "cache_hits": 0,
                "llm_calls": 0,
                "rag_lookups": 0,
                "mcp_required": 0,
                "findings_updated": 0,
                "findings_processed": len((refreshed.finding_ids if refreshed else []) or []),
            }
        job = await self.session.get(FindingAIJob, job_uuid)

        scan_uuid = job.scan_id
        scan = await self.session.get(Scan, scan_uuid)
        if scan is None:
            raise ValueError(f"Scan not found for job: {job_id}")

        finding_ids = [UUID(str(fid)) for fid in (job.finding_ids or [])]
        findings = (
            await self.session.execute(select(Finding).where(Finding.id.in_(finding_ids)))
        ).scalars().all()
        if not findings:
            await set_job_status(
                self.session,
                job.id,
                FindingAIJobStatus.FAILED,
                error_message="No findings found for AI job",
            )
            return {"findings_processed": 0, "findings_updated": 0, "cache_hits": 0, "llm_calls": 0, "rag_lookups": 0, "mcp_required": 0}

        representative = next(
            (f for f in findings if f.id == job.representative_finding_id),
            findings[0],
        )
        key = job.cache_key
        fingerprint = finding_fingerprint(representative)
        rule_id = job.rule_id
        technology = job.technology or self.context_engine.technology_for_finding(representative)
        versions = context_versions()

        scan.ai_status = "processing"
        await self.session.commit()

        logger.info(
            "AI_PIPELINE_FINDING_START",
            scan_id=str(scan_uuid),
            finding_id=str(representative.id),
            job_id=str(job.id),
            rule_id=rule_id,
            technology=technology,
            group_index=group_index,
            groups_total=groups_total,
        )

        cache_hits = 0
        llm_calls = 0
        rag_lookups = 0
        mcp_required = 0
        entry: RecommendationEntry | None = None
        sources: list[dict[str, Any]] = []
        doc_status: str | None = None

        try:
            entry = await self.cache.get(key)
            if entry is not None:
                cache_hits = 1
                payload = entry.payload or {}
                sources = normalize_sources(payload.get("sources"))
                doc_status = payload.get("documentation_status")
                await set_job_status(
                    self.session,
                    job.id,
                    FindingAIJobStatus.CACHE_HIT,
                    source=entry.source,
                    sources=sources,
                    documentation_status=doc_status,
                )
                recommendation = self._recommendation_from_entry(entry, representative, fingerprint)
                logger.info(
                    "AI_PIPELINE_CACHE_HIT",
                    scan_id=str(scan_uuid),
                    finding_id=str(representative.id),
                    rule_id=rule_id,
                    layer=getattr(entry, "source", "unknown"),
                )
                await self._broadcast_cache_hit(str(scan_uuid), rule_id, entry)
            else:
                await set_job_status(self.session, job.id, FindingAIJobStatus.RAG_RETRIEVING)
                context = await self.context_engine.build_context(
                    representative,
                    file_snippet=self.snippet_loader(scan, representative),
                )
                if context.rule_knowledge is not None:
                    rag_lookups = 1
                    docs_found = len(getattr(context.rule_knowledge, "documents", []) or [])
                    logger.info(
                        "AI_PIPELINE_RAG_COMPLETED",
                        scan_id=str(scan_uuid),
                        finding_id=str(representative.id),
                        rule_id=rule_id,
                        documents_found=docs_found,
                        method=getattr(context.rule_knowledge, "method", "unknown"),
                    )
                    await self._broadcast_rag_completed(str(scan_uuid), rule_id, context)

                if context.mcp_results:
                    mcp_required = 1
                    await set_job_status(self.session, job.id, FindingAIJobStatus.MCP_RETRIEVING)
                    mcp_statuses = [getattr(r, "status", "unknown") for r in context.mcp_results]
                    logger.info(
                        "AI_PIPELINE_MCP_COMPLETED",
                        scan_id=str(scan_uuid),
                        finding_id=str(representative.id),
                        rule_id=rule_id,
                        technology=technology,
                        results_count=len(context.mcp_results),
                        statuses=mcp_statuses,
                    )
                    await self._broadcast_mcp_completed(str(scan_uuid), rule_id, technology, context)

                sources = collect_sources(context)
                rag_enabled = bool(getattr(context, "rag_enabled", False))
                doc_status = documentation_status(
                    sources,
                    rag_attempted=rag_enabled and context.rule_knowledge is not None,
                    rag_failed=rag_enabled and context.rule_knowledge is None,
                    mcp_attempted=bool(getattr(context, "mcp_attempted", False)),
                )

                await set_job_status(self.session, job.id, FindingAIJobStatus.GENERATING)
                await self._broadcast_llm_started(str(scan_uuid), rule_id, technology)
                recommendation = await self.context_engine.generate_recommendation(
                    representative, context, fingerprint
                )
                if recommendation.ai_generated:
                    llm_calls = 1
                await self._broadcast_llm_completed(str(scan_uuid), rule_id, recommendation)

                await set_job_status(self.session, job.id, FindingAIJobStatus.SAVING)
                await self._persist_recommendation(
                    key,
                    recommendation,
                    representative,
                    scan_uuid,
                    versions,
                    context,
                    sources=sources,
                    documentation_status=doc_status,
                )
                cached = await self.cache.get(key)
                entry = cached if cached is not None else entry

            updated = await self._apply_recommendation(findings, recommendation, scan_uuid)

            patch_llm_calls = 0
            try:
                from app.services.remediation_scan_service import (
                    generate_scan_time_patch_for_finding,
                    persist_remediation_on_finding,
                )

                for finding in findings:
                    prior_meta = getattr(finding, "processing_metadata", None)
                    block = await generate_scan_time_patch_for_finding(
                        scan=scan,
                        finding=finding,
                        file_loader=self._file_loader,
                        job_id=str(job.id),
                    )
                    if block.get("unified_diff") and block.get("patch_status") in {
                        "validation_passed",
                        "patch_generated",
                    }:
                        patch_llm_calls += 1
                    await persist_remediation_on_finding(self.session, finding, block)
            except Exception as patch_exc:
                logger.warning(
                    "SCAN_PATCH_STAGE_FAILED",
                    scan_id=str(scan_uuid),
                    job_id=str(job.id),
                    error=str(patch_exc)[:300],
                )

            await self.session.commit()

            source = recommendation.source
            if mcp_required and rag_lookups:
                source = "rag_mcp"
            elif mcp_required:
                source = "mcp"
            elif rag_lookups:
                source = "rag"
            elif cache_hits:
                source = "cache"

            await set_job_status(
                self.session,
                job.id,
                FindingAIJobStatus.COMPLETED,
                source=source,
                recommendation=recommendation.to_dict(),
                sources=sources,
                documentation_status=doc_status,
            )
            job = await self.session.get(FindingAIJob, job.id)
            if job:
                job.model = versions.get("model")
                job.prompt_version = versions.get("prompt")
                job.rag_context_version = versions.get("rag")
                self.session.add(job)
                await self.session.commit()

            for finding in findings:
                await self._broadcast_recommendation_updated(
                    str(scan_uuid),
                    str(finding.id),
                    rule_id,
                    FindingAIJobStatus.COMPLETED.value,
                    source,
                    recommendation.to_dict(),
                )

            await self._broadcast_finding_completed(str(scan_uuid), group_index, groups_total)
            self._record_metrics(recommendation, entry, findings, group_index, groups_total)
            await aggregate_scan_ai_status(self.session, scan_uuid)

            return {
                "cache_hits": cache_hits,
                "llm_calls": llm_calls,
                "patch_llm_calls": patch_llm_calls,
                "rag_lookups": rag_lookups,
                "mcp_required": mcp_required,
                "findings_updated": updated,
                "findings_processed": len(findings),
            }
        except Exception as exc:
            logger.exception(
                "AI_PIPELINE_JOB_FAILED",
                scan_id=str(scan_uuid),
                job_id=str(job.id),
                rule_id=rule_id,
                error=str(exc),
            )
            await set_job_status(
                self.session,
                job.id,
                FindingAIJobStatus.FAILED,
                error_message=str(exc),
            )
            await aggregate_scan_ai_status(self.session, scan_uuid)
            raise

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
        *,
        sources: list[dict[str, Any]] | None = None,
        documentation_status: str | None = None,
    ) -> None:
        payload = recommendation.to_dict()
        payload["finding_fingerprint"] = payload.get("finding_fingerprint") or finding_fingerprint(finding)
        payload["rule_id"] = payload.get("rule_id") or str(getattr(finding, "rule_id", "") or "")
        payload["technology"] = payload.get("technology") or recommendation.technology
        payload["sources"] = sources or []
        payload["documentation_status"] = documentation_status
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

    async def _broadcast_started(
        self,
        scan_id: str,
        *,
        findings_total: int = 0,
        total_findings: int | None = None,
        info_excluded: int | None = None,
    ) -> None:
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
            if total_findings is not None:
                await scan_progress_manager.broadcast_ai_progress(
                    scan_id,
                    phase="eligibility",
                    message_text=(
                        f"AI eligible: {findings_total} of {total_findings} findings"
                        + (f" ({info_excluded} informational excluded)" if info_excluded else "")
                    ),
                    progress=0,
                    findings_processed=0,
                    findings_total=findings_total,
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

    async def _broadcast_recommendation_updated(
        self,
        scan_id: str,
        finding_id: str,
        rule_id: str,
        status: str,
        source: str | None,
        recommendation: dict[str, Any],
    ) -> None:
        try:
            from app.websockets.scan_progress import scan_progress_manager
            await scan_progress_manager.broadcast_ai_recommendation_updated(
                scan_id,
                finding_id,
                rule_id,
                status,
                source,
                recommendation,
            )
        except Exception as exc:
            logger.debug("AI_RECOMMENDATION_WS_UPDATED_ERROR", error=str(exc))

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
    from app.services.ai_recommendation_snippets import RepoFileSnippetLoader
    return RepoFileSnippetLoader(repo_scanner=_default_repo_scanner()).snippet_for


def _default_repo_scanner() -> Any:
    from app.utils.repository_scanner import RepositoryScanner
    return RepositoryScanner()


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
    session_factory: Any | None = None,
) -> AIRecommendationRunResult:
    """Entry point: run the recommendation pipeline for a scan."""
    owns_session = session is None
    if owns_session:
        from app.db.session import get_session_factory

        session_factory = session_factory or get_session_factory()
        session = session_factory()
    try:
        svc = service or AIRecommendationService(
            session=session,
            session_factory=session_factory,
        )
        return await svc.process_scan(scan_id)
    finally:
        if owns_session:
            await session.close()


async def _run_ai_job(scan_id_str: str) -> None:
    """Run AI recommendations on the main event loop (shared DB/Redis/WS clients)."""
    from app.db.session import get_session_factory

    session = get_session_factory()()
    try:
        await run_ai_recommendations_for_scan(scan_id_str, session=session)
    finally:
        await session.close()


def _schedule_ai_on_main_loop(scan_id_str: str) -> bool:
    from app.core.event_loop import schedule_coroutine
    from app.workers.tasks.ai_recommendations import _mark_scan_ai_failed

    def _on_error(exc: Exception) -> None:
        logger.exception(
            "AI_RECOMMENDATION_SCHEDULED_FAILED",
            scan_id=scan_id_str,
            error=str(exc),
        )
        _mark_scan_ai_failed(scan_id_str, str(exc))

    scheduled = schedule_coroutine(_run_ai_job(scan_id_str), on_error=_on_error)
    if scheduled is not None:
        logger.info("AI_RECOMMENDATION_ENQUEUED", scan_id=scan_id_str, transport="main_loop")
        return True
    return False


def enqueue_ai_analysis_for_scan(scan_id: UUID | str) -> None:
    """Enqueue AI analysis via Celery; fall back to the main loop or a thread.

    Never blocks or raises: the scanner already committed ``COMPLETED`` before
    this is called, so AI analysis is strictly async and scan-independent.
    """
    scan_id_str = str(scan_id)
    _mark_scan_ai_queued(scan_id_str)

    # Local dev: schedule on the FastAPI event loop — avoids cross-loop DB/RAG conflicts.
    if settings.ENVIRONMENT == "development" or not settings.CELERY_AI_TASKS_ENABLED:
        if _schedule_ai_on_main_loop(scan_id_str):
            return
        logger.warning("AI_RECOMMENDATION_MAIN_LOOP_UNAVAILABLE", scan_id=scan_id_str)
        _start_thread_fallback(scan_id_str)
        return

    try:
        from app.workers.tasks.ai_recommendations import enqueue_ai_analysis
        enqueue_ai_analysis.delay(scan_id_str)
        logger.info("AI_RECOMMENDATION_ENQUEUED", scan_id=scan_id_str, transport="celery")
        _schedule_stale_watchdog(scan_id_str)
        return
    except Exception as exc:
        logger.warning(
            "AI_RECOMMENDATION_CELERY_UNAVAILABLE",
            scan_id=scan_id_str,
            error=str(exc)[:300],
        )

    if _schedule_ai_on_main_loop(scan_id_str):
        return
    _start_thread_fallback(scan_id_str)


def _mark_scan_ai_queued(scan_id: str) -> None:
    from app.models.scan import Scan
    from sqlalchemy import select

    from app.db.session import get_sync_session_factory

    session = get_sync_session_factory()()
    try:
        scan = session.execute(
            select(Scan).where(Scan.id == uuid_mod.UUID(scan_id))
        ).scalar_one_or_none()
        if scan and scan.ai_status in (None, "pending", "failed"):
            scan.ai_status = "queued"
            scan.ai_error_message = None
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def _schedule_stale_watchdog(scan_id: str, delay_seconds: int = 45) -> None:
    """If Celery workers never pick up the job, fall back to in-process execution."""
    import threading

    def _watchdog() -> None:
        import time
        time.sleep(delay_seconds)
        from app.models.scan import Scan
        from sqlalchemy import select

        from app.db.session import get_sync_session_factory

        session = get_sync_session_factory()()
        try:
            scan = session.execute(
                select(Scan).where(Scan.id == uuid_mod.UUID(scan_id))
            ).scalar_one_or_none()
            if scan and scan.ai_status in ("queued", "pending"):
                logger.warning(
                    "AI_RECOMMENDATION_CELERY_STALE_FALLBACK",
                    scan_id=scan_id,
                    ai_status=scan.ai_status,
                )
                if settings.ENVIRONMENT == "development" or not settings.CELERY_AI_TASKS_ENABLED:
                    if _schedule_ai_on_main_loop(scan_id):
                        return
                _start_thread_fallback(scan_id)
        finally:
            session.close()

    threading.Thread(
        target=_watchdog,
        name=f"ai-watchdog-{scan_id[:8]}",
        daemon=True,
    ).start()


async def _run_ai_recommendations_in_isolated_loop(scan_id: str) -> None:
    """Run AI pipeline on a dedicated engine/session (safe for background threads)."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import settings

    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    try:
        async with session_factory() as session:
            await run_ai_recommendations_for_scan(
                scan_id,
                session=session,
                session_factory=session_factory,
            )
    finally:
        await engine.dispose()


def _start_thread_fallback(scan_id: str) -> None:
    def _fallback_runner() -> None:
        try:
            asyncio.run(_run_ai_recommendations_in_isolated_loop(scan_id))
        except Exception as run_exc:  # pragma: no cover - defensive
            logger.exception(
                "AI_RECOMMENDATION_FALLBACK_FAILED",
                scan_id=scan_id,
                error=str(run_exc),
            )

    import threading

    thread = threading.Thread(
        target=_fallback_runner,
        name=f"ai-recommendations-{scan_id[:8]}",
        daemon=True,
    )
    thread.start()
    logger.info("AI_RECOMMENDATION_ENQUEUED", scan_id=scan_id, transport="thread")
