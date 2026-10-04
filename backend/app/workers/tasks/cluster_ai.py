"""Celery tasks for Kubernetes cluster AI analysis."""

from __future__ import annotations

import asyncio
import threading
import time
import uuid as uuid_mod
from datetime import UTC, datetime
from typing import Any

import structlog

from app.workers.celery_config import celery_app

logger = structlog.get_logger(__name__)

_TASK = "app.workers.tasks.cluster_ai.process_cluster_ai_job"
_ACTIVE_STATUSES = frozenset({
    "queued",
    "running",
    "collecting",
    "checking_cache",
    "rag_retrieving",
    "mcp_retrieving",
    "generating",
})


def _run_async(coro_builder: Any) -> Any:
    """Run async code in an isolated loop — for Celery workers only."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import settings

    async def _wrapper() -> Any:
        engine = create_async_engine(settings.DATABASE_URL, pool_size=1, max_overflow=0)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with session_factory() as session:
                return await coro_builder(session)
        finally:
            await engine.dispose()

    return asyncio.run(_wrapper())


async def _mark_job_failed(session: Any, job_id: str, exc: Exception) -> None:
    from sqlalchemy import select

    from app.models.cluster_ai_job import ClusterAIJob, ClusterAIJobStatus

    result = await session.execute(
        select(ClusterAIJob).where(ClusterAIJob.id == uuid_mod.UUID(job_id))
    )
    job = result.scalar_one_or_none()
    if job and job.status != ClusterAIJobStatus.COMPLETED.value:
        job.status = ClusterAIJobStatus.FAILED.value
        job.error_message = str(exc)[:500]
        job.completed_at = datetime.now(UTC)
        await session.commit()


async def _process_job_with_session(job_id: str) -> dict[str, Any]:
    """Run on the FastAPI main event loop — avoids cross-loop DB/Redis conflicts."""
    from app.db.session import get_session_factory

    session = get_session_factory()()
    try:
        return await _process_job(session, job_id)
    except Exception as exc:
        await session.rollback()
        await _mark_job_failed(session, job_id, exc)
        raise
    finally:
        await session.close()


def _enqueue_on_main_loop(job_id: str) -> bool:
    """Schedule job on the uvicorn event loop (safe for dev / in-process)."""
    from app.core.event_loop import schedule_coroutine

    future = schedule_coroutine(
        _process_job_with_session(job_id),
        on_error=lambda exc: logger.exception(
            "CLUSTER_AI_JOB_FAILED", job_id=job_id, error=str(exc),
        ),
    )
    return future is not None


async def _process_job(session: Any, job_id: str) -> dict[str, Any]:
    from sqlalchemy import select

    from app.kubernetes.cache import get_cluster_cache
    from app.kubernetes.cluster_ai_engine import get_cluster_ai_engine
    from app.kubernetes.connectors.factory import build_connector
    from app.kubernetes.service import get_or_collect_snapshot
    from app.kubernetes.upgrade_collector import collect_upgrade_discovery
    from app.kubernetes.upgrade_readiness import analyze_upgrade_readiness
    from app.models.cluster_ai_job import ClusterAIJob, ClusterAIJobStatus
    from app.models.kubernetes import KubernetesConnection

    result = await session.execute(select(ClusterAIJob).where(ClusterAIJob.id == uuid_mod.UUID(job_id)))
    job = result.scalar_one_or_none()
    if not job:
        return {"status": "not_found"}

    conn_result = await session.execute(
        select(KubernetesConnection).where(KubernetesConnection.id == job.connection_id)
    )
    connection = conn_result.scalar_one_or_none()
    if not connection:
        job.status = ClusterAIJobStatus.FAILED.value
        job.error_message = "Connection not found"
        await session.commit()
        return {"status": "failed"}

    job.status = ClusterAIJobStatus.RUNNING.value
    job.started_at = datetime.now(UTC)
    await session.commit()

    request_meta = (job.result or {}).get("_request", {}) if isinstance(job.result, dict) else {}
    analysis_type = job.analysis_type or "copilot"
    cache = get_cluster_cache()
    engine = get_cluster_ai_engine()

    if analysis_type == "upgrade":
        job.status = ClusterAIJobStatus.COLLECTING.value
        await session.commit()

        snapshot = await get_or_collect_snapshot(connection, session, force_refresh=True)
        k8s_version = snapshot.get("kubernetes_version", "unknown")
        target_version = request_meta.get("target_version") or "v1.34"

        cached = await cache.get_upgrade_analysis(
            str(connection.id), k8s_version, target_version
        )
        if cached and not request_meta.get("force_refresh"):
            result_dict = cached
            result_dict["source"] = "cache"
        else:
            connector = await build_connector(connection, session)
            discovery = await collect_upgrade_discovery(connector)

            job.status = ClusterAIJobStatus.RUNNING.value
            await session.commit()

            upgrade_result = analyze_upgrade_readiness(
                current_version=k8s_version,
                target_version=target_version,
                discovery=discovery,
                provider=connection.provider,
                kind=connection.kind,
                region=connection.aws_region,
            )
            upgrade_result["analyzed_at"] = datetime.now(UTC).isoformat()

            job.status = ClusterAIJobStatus.RAG_RETRIEVING.value
            await session.commit()

            # Optional RAG enrichment for migration guidance (no secrets)
            rag_notes: list[str] = []
            try:
                from app.rag.service import get_rag_service

                rag = get_rag_service()
                for api in upgrade_result.get("blocking_issues", [])[:3]:
                    rule_id = f"k8s-api-{api.get('api', '').replace('/', '-')}"
                    knowledge = await rag.get_rule_knowledge(rule_id, technology="kubernetes")
                    if knowledge and getattr(knowledge, "chunks", None):
                        rag_notes.append(
                            knowledge.chunks[0].content[:500] if knowledge.chunks else ""
                        )
            except Exception as exc:
                logger.debug("UPGRADE_RAG_SKIP", error=str(exc))

            upgrade_result["rag_guidance"] = [n for n in rag_notes if n]
            result_dict = upgrade_result
            await cache.set_upgrade_analysis(
                str(connection.id), k8s_version, target_version, upgrade_result
            )

        job.status = ClusterAIJobStatus.COMPLETED.value
        job.result = result_dict
        job.finding_count = len(result_dict.get("blocking_issues", []))
        job.recommendation_count = len(result_dict.get("warnings", []))
        job.completed_at = datetime.now(UTC)
        await session.commit()
        return {"status": "completed", "job_id": job_id}

    snapshot = await get_or_collect_snapshot(connection, session, force_refresh=False)

    if analysis_type == "troubleshoot":
        job.status = ClusterAIJobStatus.COLLECTING.value
        await session.commit()
        question = request_meta.get("question") or "What issues exist in this cluster?"

        job.status = ClusterAIJobStatus.RAG_RETRIEVING.value
        await session.commit()

        result_dict = await engine.run_troubleshoot(snapshot, question)
    else:
        job.status = ClusterAIJobStatus.RAG_RETRIEVING.value
        await session.commit()

        result_dict = await engine.run_copilot_analysis(snapshot)

    job.status = ClusterAIJobStatus.COMPLETED.value
    job.result = result_dict
    job.finding_count = result_dict.get("finding_count", 0)
    job.recommendation_count = result_dict.get("recommendation_count", 0)
    job.completed_at = datetime.now(UTC)
    await session.commit()

    await cache.set_ai_result(str(connection.id), str(job.id), result_dict)

    return {"status": "completed", "job_id": job_id}


def run_cluster_ai_job(job_id: str) -> dict[str, Any]:
    """Run a cluster AI job in an isolated loop (Celery worker process)."""
    logger.info("CLUSTER_AI_JOB_STARTED", job_id=job_id, transport="celery_isolated")
    try:
        return _run_async(lambda session: _process_job(session, job_id))
    except Exception as exc:
        logger.exception("CLUSTER_AI_JOB_FAILED", job_id=job_id, error=str(exc))
        _run_async(lambda session: _mark_job_failed(session, job_id, exc))
        raise


def _start_thread_fallback(job_id: str) -> None:
    """Last-resort fallback when the main event loop is not available."""

    def _run() -> None:
        try:
            run_cluster_ai_job(job_id)
        except Exception:
            logger.exception("CLUSTER_AI_THREAD_FAILED", job_id=job_id)

    threading.Thread(
        target=_run,
        name=f"cluster-ai-{job_id[:8]}",
        daemon=True,
    ).start()


def _schedule_stale_watchdog(job_id: str, delay_seconds: int = 30) -> None:
    """If Celery never picks up the job, re-enqueue on the main loop."""

    def _watchdog() -> None:
        time.sleep(delay_seconds)
        try:
            from sqlalchemy import select

            from app.db.session import get_sync_session_factory
            from app.models.cluster_ai_job import ClusterAIJob

            sync_session = get_sync_session_factory()
            with sync_session() as session:
                result = session.execute(
                    select(ClusterAIJob).where(ClusterAIJob.id == uuid_mod.UUID(job_id))
                )
                job = result.scalar_one_or_none()
            if job and job.status in _ACTIVE_STATUSES:
                logger.warning(
                    "CLUSTER_AI_CELERY_STALE_FALLBACK",
                    job_id=job_id,
                    status=job.status,
                )
                from app.config import settings

                if settings.ENVIRONMENT == "development" or not settings.CELERY_AI_TASKS_ENABLED:
                    if not _enqueue_on_main_loop(job_id):
                        _start_thread_fallback(job_id)
                else:
                    _start_thread_fallback(job_id)
        except Exception:
            logger.exception("CLUSTER_AI_WATCHDOG_FAILED", job_id=job_id)

    threading.Thread(
        target=_watchdog,
        name=f"cluster-ai-watchdog-{job_id[:8]}",
        daemon=True,
    ).start()


def enqueue_cluster_ai_job(job_id: str) -> None:
    """Enqueue via Celery when available; in dev, schedule on the main event loop."""
    from app.config import settings

    # Local dev: schedule on the FastAPI event loop — never asyncio.run() in threads.
    if settings.ENVIRONMENT == "development" or not settings.CELERY_AI_TASKS_ENABLED:
        if _enqueue_on_main_loop(job_id):
            logger.info("CLUSTER_AI_JOB_ENQUEUED", job_id=job_id, transport="main_loop")
            return
        logger.warning("CLUSTER_AI_MAIN_LOOP_UNAVAILABLE", job_id=job_id)
        _start_thread_fallback(job_id)
        return

    try:
        process_cluster_ai_job.delay(job_id)
        logger.info("CLUSTER_AI_JOB_ENQUEUED", job_id=job_id, transport="celery")
    except Exception as exc:
        logger.warning(
            "CLUSTER_AI_CELERY_UNAVAILABLE",
            job_id=job_id,
            error=str(exc)[:300],
        )
        _start_thread_fallback(job_id)
        return

    _schedule_stale_watchdog(job_id)


@celery_app.task(
    name=_TASK,
    bind=True,
    max_retries=2,
    default_retry_delay=15,
    acks_late=True,
    task_track_started=True,
)
def process_cluster_ai_job(self: Any, job_id: str) -> dict[str, Any]:
    """Process a cluster AI analysis job asynchronously."""
    logger.info("CLUSTER_AI_JOB_STARTED", job_id=job_id, task_id=self.request.id)
    return run_cluster_ai_job(job_id)
