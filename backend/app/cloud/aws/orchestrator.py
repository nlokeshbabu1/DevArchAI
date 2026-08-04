"""Cloud Scan Orchestrator — coordinates scanners and persists results.

Architecture:
  Scanner -> CloudResourceData -> Repository -> PostgreSQL

The orchestrator:
  1. Builds boto3 session via STS AssumeRole
  2. Discovers regions
  3. Runs all 15 scanners (discovery + security + cost)
  4. Persists results via Repository layer (batch upsert, sanitized JSON)
  5. Emits WebSocket events for real-time UI updates

Scanners never touch SQLAlchemy. All persistence goes through repositories.
"""

from __future__ import annotations

import time
import traceback
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import boto3
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cloud.aws.scanners import ALL_SCANNERS
from app.cloud.base import (
    CloudCostData,
    CloudFindingData,
    CloudResourceData,
)
from app.cloud.repository import (
    AIRecommendationRepository,
    CloudComplianceRepository,
    CloudCostRepository,
    CloudFindingRepository,
    CloudResourceRepository,
)
from app.cloud.websocket_manager import cloud_ws_manager
from app.core.encryption import get_encryption_service
from app.engines.cloud_recommendation_engine import (
    CloudRecommendation,
    get_recommendation_engine,
)
from app.models.cloud import (
    CloudConnection,
    CloudResource,
    CloudScanSession,
)

logger = structlog.get_logger(__name__)

STAGE_ORDER = [
    "initialize",
    "scan_resources",
    "security_analysis",
    "cost_analysis",
    "compliance_check",
    "ai_recommendations",
    "finalize",
]


SERVICE_CATEGORY: dict[str, str] = {
    "ec2": "security", "vpc": "networking", "s3": "storage",
    "iam": "iam", "lambda": "compute", "rds": "storage",
    "dynamodb": "storage", "elasticache": "storage", "kms": "security",
    "cloudtrail": "security", "config": "compliance", "guardduty": "security",
    "waf": "security", "shield": "security", "sns": "networking",
    "sqs": "networking", "elb": "networking", "alb": "networking",
    "cloudfront": "networking", "route53": "networking",
    "ecs": "compute", "eks": "compute", "batch": "compute",
    "stepfunctions": "compute", "glue": "compute",
    "redshift": "storage", "elasticsearch": "storage",
    "kinesis": "networking", "firehose": "networking",
}


class CloudScanOrchestrator:
    """Coordinates all cloud scanners, persists results, emits WS events."""

    async def run_full_scan(
        self,
        connection_id: str,
        db: AsyncSession,
    ) -> None:
        logger.info(
            "SCAN_STARTED",
            connection_id=connection_id,
            timestamp=datetime.now(UTC).isoformat(),
        )

        conn = await self._load_connection(db, connection_id)
        if conn is None:
            logger.error("SCAN_CONNECTION_NOT_FOUND", connection_id=connection_id)
            return

        session_record = await self._create_scan_session(db, conn)
        scan_session_id = str(session_record.id)
        cid = str(conn.id)

        await cloud_ws_manager.stage_start(cid, "initialize", "Preparing cloud scan")

        # ── Stage: initialize — build boto session and verify identity ──
        try:
            session = await self._build_boto_session(conn)
        except Exception as exc:
            tb = traceback.format_exc()
            logger.error(
                "SCAN_INIT_FAILED",
                connection_id=connection_id,
                error=str(exc),
                traceback=tb,
            )
            await self._fail(db, conn, session_record, str(exc))
            return

        # ── Verify caller identity ──
        try:
            await self._log_caller_identity(session, conn)
        except Exception as exc:
            logger.warning(
                "CALLER_IDENTITY_CHECK_FAILED",
                connection_id=connection_id,
                error=str(exc),
            )

        # ── Discover all enabled regions ──
        try:
            regions = await self._discover_regions(session, conn)
        except Exception as exc:
            logger.warning(
                "REGION_DISCOVERY_FAILED",
                connection_id=connection_id,
                error=str(exc),
                fallback_regions=conn.regions,
            )
            regions = conn.regions or ["us-east-1"]

        logger.info(
            "SCAN_REGIONS_DISCOVERED",
            connection_id=connection_id,
            regions=regions,
            region_count=len(regions),
        )

        all_resources: list[CloudResourceData] = []
        all_findings: list[CloudFindingData] = []
        all_costs: list[CloudCostData] = []
        total_stages = len(STAGE_ORDER)
        scanner_errors: list[dict[str, str]] = []

        await cloud_ws_manager.stage_complete(cid, "initialize")
        await self._update_progress(db, session_record, 1, "initialize", total_stages)

        # ── Stage: scan resources ──
        await cloud_ws_manager.stage_start(cid, "scan_resources", "Scanning cloud resources")
        await self._update_progress(db, session_record, 2, "scan_resources", total_stages)
        logger.info(
            "STAGE_SCAN_RESOURCES_STARTED",
            connection_id=connection_id,
            scanner_count=len(ALL_SCANNERS),
        )

        for i, scanner in enumerate(ALL_SCANNERS):
            stage_progress = ((i / len(ALL_SCANNERS)) * 100)
            await cloud_ws_manager.stage_progress(
                cid, "scan_resources", stage_progress,
                f"Scanning {scanner.service_name}",
            )
            scanner_start = time.time()
            logger.info(
                "SCANNER_STARTING",
                scanner=scanner.service_name,
                regions=regions,
                step=f"{i + 1}/{len(ALL_SCANNERS)}",
            )
            try:
                resources = await scanner.scan(session, regions)
                scanner_duration = round(time.time() - scanner_start, 2)

                # Log resource-level details for each scanned service
                svc_resource_ids = []
                for r in resources:
                    svc_resource_ids.append(
                        f"{r.service}/{r.region}/{r.resource_id}({r.resource_type})"
                    )
                    logger.debug(
                        "RESOURCE_FETCHED_FROM_AWS: service=%s region=%s resource_id=%s "
                        "resource_name=%s resource_type=%s status=%s",
                        r.service, r.region, r.resource_id,
                        r.resource_name, r.resource_type, r.status,
                    )

                logger.info(
                    "SCANNER_COMPLETED: service=%s region_count=%d resources_fetched_from_aws=%d "
                    "duration_seconds=%.2f resource_ids=[%s]",
                    scanner.service_name, len(regions), len(resources),
                    scanner_duration, ",".join(svc_resource_ids[:20]) if svc_resource_ids else "none",
                )
                all_resources.extend(resources)
            except Exception as exc:
                scanner_duration = round(time.time() - scanner_start, 2)
                tb = traceback.format_exc()
                logger.error(
                    "SCANNER_FAILED",
                    scanner=scanner.service_name,
                    error=str(exc),
                    traceback=tb,
                    duration_seconds=scanner_duration,
                )
                scanner_errors.append({"scanner": scanner.service_name, "error": str(exc)})
                await cloud_ws_manager.stage_progress(
                    cid, "scan_resources", stage_progress,
                    f"Warning: {scanner.service_name} scanner failed",
                )

        logger.info(
            "STAGE_SCAN_RESOURCES_COMPLETED",
            connection_id=connection_id,
            total_resources=len(all_resources),
            scanner_errors=len(scanner_errors),
        )
        await cloud_ws_manager.stage_complete(
            cid, "scan_resources",
            resource_count=len(all_resources),
        )

        # If no resources found AND all scanners failed, treat as scan failure
        if len(all_resources) == 0 and len(scanner_errors) == len(ALL_SCANNERS):
            error_summary = "; ".join(f"{e['scanner']}: {e['error']}" for e in scanner_errors[:3])
            await self._fail(db, conn, session_record, f"All scanners failed: {error_summary}")
            return

        # ── Stage: security analysis ──
        await cloud_ws_manager.stage_start(cid, "security_analysis", "Analyzing security posture")
        await self._update_progress(db, session_record, 3, "security_analysis", total_stages)
        logger.info("STAGE_SECURITY_STARTED", connection_id=connection_id)

        for i, scanner in enumerate(ALL_SCANNERS):
            stage_progress = ((i / len(ALL_SCANNERS)) * 100)
            await cloud_ws_manager.stage_progress(
                cid, "security_analysis", stage_progress,
                f"Checking {scanner.service_name} security",
            )
            try:
                svc_resources = [r for r in all_resources if r.service == scanner.service_name]
                findings = await scanner.check_security(session, svc_resources)
                all_findings.extend(findings)
                if findings:
                    logger.info(
                        "SECURITY_FINDINGS_FOUND",
                        scanner=scanner.service_name,
                        findings_count=len(findings),
                    )
                for f in findings:
                    await cloud_ws_manager.finding_discovered(cid, {
                        "title": f.title,
                        "severity": f.severity,
                        "category": f.category,
                        "service": f.service,
                    })
            except Exception as exc:
                tb = traceback.format_exc()
                logger.error(
                    "SECURITY_CHECK_FAILED",
                    scanner=scanner.service_name,
                    error=str(exc),
                    traceback=tb,
                )

        logger.info(
            "STAGE_SECURITY_COMPLETED",
            connection_id=connection_id,
            total_findings=len(all_findings),
        )
        await cloud_ws_manager.stage_complete(
            cid, "security_analysis",
            finding_count=len(all_findings),
        )

        # ── Stage: cost analysis ──
        await cloud_ws_manager.stage_start(cid, "cost_analysis", "Analyzing cost optimization")
        await self._update_progress(db, session_record, 4, "cost_analysis", total_stages)
        logger.info("STAGE_COST_STARTED", connection_id=connection_id)

        for i, scanner in enumerate(ALL_SCANNERS):
            stage_progress = ((i / len(ALL_SCANNERS)) * 100)
            await cloud_ws_manager.stage_progress(
                cid, "cost_analysis", stage_progress,
                f"Checking {scanner.service_name} costs",
            )
            try:
                svc_resources = [r for r in all_resources if r.service == scanner.service_name]
                costs = await scanner.check_cost(session, svc_resources)
                all_costs.extend(costs)
                if costs:
                    logger.info(
                        "COST_RECOMMENDATIONS_FOUND",
                        scanner=scanner.service_name,
                        recommendations_count=len(costs),
                    )
            except Exception as exc:
                tb = traceback.format_exc()
                logger.error(
                    "COST_CHECK_FAILED",
                    scanner=scanner.service_name,
                    error=str(exc),
                    traceback=tb,
                )

        logger.info(
            "STAGE_COST_COMPLETED",
            connection_id=connection_id,
            total_cost_recommendations=len(all_costs),
        )
        await cloud_ws_manager.stage_complete(cid, "cost_analysis")

        # ── Stage: compliance check ──
        await cloud_ws_manager.stage_start(cid, "compliance_check", "Running compliance checks")
        await self._update_progress(db, session_record, 5, "compliance_check", total_stages)
        compliance_results = self._compute_compliance(all_findings)
        logger.info(
            "STAGE_COMPLIANCE_COMPLETED",
            connection_id=connection_id,
            frameworks=len(compliance_results),
        )
        await cloud_ws_manager.stage_complete(cid, "compliance_check")

        # ── Stage: AI Recommendations (knowledge-enriched) ──
        ai_recommendation_rows: list[dict[str, Any]] = []
        from app.config import settings as _cfg

        if _cfg.AI_RECOMMENDATIONS_ENABLED:
            await cloud_ws_manager.stage_start(
                cid, "ai_recommendations", "Generating AI recommendations"
            )
            await self._update_progress(
                db, session_record, 6, "ai_recommendations", total_stages
            )
            logger.info("STAGE_AI_RECOMMENDATIONS_STARTED", connection_id=connection_id)

            try:
                finding_dicts = [
                    {
                        "title": f.title,
                        "severity": f.severity,
                        "category": f.category,
                        "service": f.service,
                        "resource_id": f.resource_id or "",
                        "resource_type": f.resource_type or "",
                        "region": f.region,
                        "rule_id": f.rule_id or "",
                        "description": f.description,
                        "evidence": f.evidence,
                        "compliance_frameworks": f.compliance_frameworks,
                    }
                    for f in all_findings
                ]

                engine = get_recommendation_engine()
                llm_recs = await engine.generate_recommendations(
                    finding_dicts,
                    service="",
                    connection_id=str(conn.id),
                    scan_session_id=str(session_record.id),
                    max_recommendations=_cfg.AI_RECOMMENDATIONS_MAX_PER_SCAN,
                )
                logger.info(
                    "recommendations_generated connection_id=%s scan_id=%s recommendation_count=%d",
                    connection_id, scan_session_id, len(llm_recs),
                )
            except Exception as exc:
                tb = traceback.format_exc()
                logger.error(
                    "AI_RECOMMENDATIONS_FAILED connection_id=%s scan_id=%s error=%s traceback=%s",
                    connection_id, scan_session_id, str(exc), tb,
                )
                llm_recs = []

            # Ensure EVERY finding gets at least one recommendation (fallback for gaps)
            all_recs = self._ensure_all_findings_have_recs(
                all_findings, llm_recs, conn.id, session_record.id,
            )

            ai_recommendation_rows = [
                self._recommendation_to_row(r, conn, session_record.id)
                for r in all_recs
            ]
            logger.info(
                "recommendations_generated connection_id=%s scan_id=%s recommendation_count=%d",
                connection_id, scan_session_id, len(ai_recommendation_rows),
            )

            await cloud_ws_manager.stage_complete(cid, "ai_recommendations")
        else:
            logger.info("AI_RECOMMENDATIONS_SKIPPED reason=disabled")
            await cloud_ws_manager.stage_complete(cid, "ai_recommendations")

        # ── Stage: finalize — persist via repositories ──
        await cloud_ws_manager.stage_start(cid, "finalize", "Saving results")
        await self._update_progress(db, session_record, 7, "finalize", total_stages)

        try:
            persist_stats = await self._persist_results(
                db=db,
                conn=conn,
                session_record=session_record,
                resources=all_resources,
                findings=all_findings,
                costs=all_costs,
                compliance=compliance_results,
                ai_recommendations=ai_recommendation_rows,
            )
        except Exception as exc:
            tb = traceback.format_exc()
            logger.error(
                "PERSIST_FAILED",
                connection_id=connection_id,
                scan_id=scan_session_id,
                error=str(exc),
                traceback=tb,
            )
            await db.rollback()
            await self._fail(db, conn, session_record, f"Persist failed: {exc}")
            await cloud_ws_manager.stage_complete(cid, "finalize")
            return

        # Update connection aggregate stats — count only active resources
        conn.resource_count = persist_stats["active_resource_count"]
        conn.finding_count = persist_stats["findings_inserted"]
        conn.security_score = self._compute_security_score(all_findings)
        conn.estimated_monthly_cost = sum(c.monthly_savings for c in all_costs)
        conn.scan_status = "completed"
        conn.scan_progress = 100.0

        session_record.status = "completed"
        session_record.progress = 100.0
        session_record.stages_completed = STAGE_ORDER.copy()
        session_record.resources_scanned = persist_stats["resources_upserted"]
        session_record.findings_count = persist_stats["findings_inserted"]
        finished_at = datetime.now(UTC)
        session_record.finished_at = finished_at
        if session_record.started_at:
            session_record.duration_seconds = round(
                (finished_at - session_record.started_at).total_seconds(), 2
            )

        try:
            await db.commit()
        except Exception as exc:
            tb = traceback.format_exc()
            logger.error(
                "COMMIT_FAILED",
                connection_id=connection_id,
                scan_id=scan_session_id,
                error=str(exc),
                traceback=tb,
            )
            await db.rollback()
            await self._fail(db, conn, session_record, f"Commit failed: {exc}")
            await cloud_ws_manager.stage_complete(cid, "finalize")
            return

        scan_duration = session_record.duration_seconds or 0.0
        logger.info(
            "SCAN_PERSISTED",
            connection_id=connection_id,
            resources_upserted=persist_stats["resources_upserted"],
            resources_skipped=persist_stats["resources_skipped"],
            findings_inserted=persist_stats["findings_inserted"],
            costs_inserted=persist_stats["costs_inserted"],
            compliance_inserted=persist_stats["compliance_inserted"],
            duration_seconds=scan_duration,
        )

        await cloud_ws_manager.stage_complete(cid, "finalize")
        await cloud_ws_manager.scan_complete(cid, {
            "resource_count": persist_stats["resources_upserted"],
            "finding_count": persist_stats["findings_inserted"],
            "security_score": conn.security_score,
            "estimated_monthly_savings": conn.estimated_monthly_cost,
            "scan_session_id": scan_session_id,
        })

        logger.info(
            "SCAN_COMPLETED",
            connection_id=connection_id,
            resources=persist_stats["resources_upserted"],
            findings=persist_stats["findings_inserted"],
            duration_seconds=scan_duration,
            regions_scanned=regions,
            scanner_errors=len(scanner_errors),
        )

    # ── private helpers ──

    async def _load_connection(self, db: AsyncSession, connection_id: str) -> CloudConnection | None:
        result = await db.execute(select(CloudConnection).where(CloudConnection.id == connection_id))
        return result.scalar_one_or_none()

    async def _create_scan_session(self, db: AsyncSession, conn: CloudConnection) -> CloudScanSession:
        now = datetime.now(UTC)
        session_record = CloudScanSession(
            connection_id=conn.id,
            status="running",
            progress=0.0,
            stages_total=len(STAGE_ORDER),
            stages_completed=[],
            started_at=now,
        )
        db.add(session_record)
        conn.scan_status = "scanning"
        conn.scan_progress = 0.0
        await db.flush()
        return session_record

    async def _build_boto_session(self, conn: CloudConnection) -> boto3.Session:
        from app.cloud.aws.sts import assume_customer_role

        encryption = get_encryption_service()
        decrypted_id = encryption.decrypt(conn.external_id_encrypted)

        logger.info(
            "ASSUMING_CUSTOMER_ROLE",
            connection_id=str(conn.id),
            account_id=conn.account_id,
            role_arn=conn.role_arn,
            session_name=f"devarchai-cloud-{conn.account_id}",
        )

        return assume_customer_role(
            customer_account_id=conn.account_id,
            customer_role_name=conn.role_arn.split("/")[-1],
            external_id=decrypted_id,
            session_name=f"devarchai-cloud-{conn.account_id}",
        )

    async def _log_caller_identity(self, session: boto3.Session, conn: CloudConnection) -> None:
        """Verify and log the caller identity after assuming the customer role."""
        import asyncio

        sts = session.client("sts")
        identity = await asyncio.to_thread(sts.get_caller_identity)

        arn = identity.get("Arn", "unknown")
        account = identity.get("Account", "unknown")
        user_id = identity.get("UserId", "unknown")

        resource = arn.split(":")[-1] if ":" in arn else ""
        role_name = resource.split("/")[-1] if "/" in resource else resource

        logger.info(
            "CALLER_IDENTITY_VERIFIED",
            connection_id=str(conn.id),
            aws_account=account,
            caller_arn=arn,
            caller_user_id=user_id,
            assumed_role_name=role_name,
            expected_account=conn.account_id,
            account_match=account == conn.account_id,
        )

        if account != conn.account_id:
            logger.warning(
                "ACCOUNT_MISMATCH",
                connection_id=str(conn.id),
                expected=conn.account_id,
                actual=account,
            )

    async def _discover_regions(self, session: boto3.Session, conn: CloudConnection) -> list[str]:
        """Discover all enabled AWS regions using DescribeRegions."""
        import asyncio

        if conn.regions and len(conn.regions) > 1:
            logger.info(
                "USING_CONFIGURED_REGIONS",
                connection_id=str(conn.id),
                regions=conn.regions,
            )
            return conn.regions

        default_region = (conn.regions or ["us-east-1"])[0]
        ec2 = session.client("ec2", region_name=default_region)

        try:
            response = await asyncio.to_thread(ec2.describe_regions, AllRegions=False)
            regions = [r["RegionName"] for r in response.get("Regions", [])]
            logger.info(
                "REGIONS_DISCOVERED",
                connection_id=str(conn.id),
                regions=regions,
                region_count=len(regions),
                source="DescribeRegions",
            )
            return regions
        except Exception as exc:
            logger.warning(
                "DESCRIBE_REGIONS_FAILED",
                connection_id=str(conn.id),
                error=str(exc),
                fallback=conn.regions or ["us-east-1"],
            )
            return conn.regions or ["us-east-1"]

    async def _update_progress(
        self,
        db: AsyncSession,
        session_record: CloudScanSession,
        stages_completed: int,
        current_stage: str,
        total_stages: int,
    ) -> None:
        session_record.stages_completed = STAGE_ORDER[:stages_completed]
        session_record.current_stage = current_stage
        session_record.progress = (stages_completed / total_stages) * 100
        await db.flush()

    async def _fail(
        self,
        db: AsyncSession,
        conn: CloudConnection,
        session_record: CloudScanSession,
        error: str,
    ) -> None:
        conn.scan_status = "failed"
        conn.scan_progress = 0.0
        session_record.status = "failed"
        session_record.error = error
        finished_at = datetime.now(UTC)
        session_record.finished_at = finished_at
        if session_record.started_at:
            session_record.duration_seconds = round(
                (finished_at - session_record.started_at).total_seconds(), 2
            )
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            await db.commit()
        await cloud_ws_manager.scan_failed(str(conn.id), error)

    async def _persist_results(
        self,
        db: AsyncSession,
        conn: CloudConnection,
        session_record: CloudScanSession,
        resources: list[CloudResourceData],
        findings: list[CloudFindingData],
        costs: list[CloudCostData],
        compliance: list[dict[str, Any]],
        ai_recommendations: list[dict[str, Any]] | None = None,
    ) -> dict[str, int]:
        """Persist all scan results via repositories.

        Uses batch upsert for resources (ON CONFLICT DO UPDATE).
        Uses batch insert for findings, costs, compliance.
        Soft-deletes resources not seen in this scan via last_scan_id comparison.

        Returns dict with counts: resources_upserted, resources_skipped,
        findings_inserted, findings_skipped, costs_inserted, compliance_inserted,
        ai_recommendations_inserted.
        """
        t0 = time.time()
        scan_id = str(session_record.id)
        logger.info(
            "PERSIST_START",
            connection_id=str(conn.id),
            scan_id=scan_id,
            resources_to_persist=len(resources),
            findings_to_persist=len(findings),
            costs_to_persist=len(costs),
            compliance_to_persist=len(compliance),
            ai_recommendations_to_persist=len(ai_recommendations or []),
        )

        # Initialize repositories
        resource_repo = CloudResourceRepository(db)
        finding_repo = CloudFindingRepository(db)
        cost_repo = CloudCostRepository(db)
        compliance_repo = CloudComplianceRepository(db)
        ai_repo = AIRecommendationRepository(db)

        # ── Resources: UPSERT + soft-delete stale ──
        resources_upserted, resources_skipped, resource_errors = await resource_repo.bulk_upsert_legacy(
            resources=resources,
            connection_id=conn.id,
            account_id=conn.account_id,
            scan_id=scan_id,
        )

        if resource_errors:
            for err in resource_errors:
                logger.warning(
                    "RESOURCE_SKIPPED",
                    resource_id=err["resource_id"],
                    resource_type=err["resource_type"],
                    service=err["service"],
                    error=err["error"],
                )

        deleted_count = await resource_repo.delete_stale(conn.id, scan_id)

        # ── Findings: UPSERT + mark stale as resolved ──
        findings_upserted, findings_skipped, finding_errors = await finding_repo.bulk_upsert(
            findings=findings,
            connection_id=conn.id,
            provider=conn.provider,
            scan_id=scan_id,
        )
        finding_stale_count = await finding_repo.mark_stale(conn.id, scan_id)

        # ── Cost Recommendations: UPSERT + mark stale as resolved ──
        costs_upserted = await cost_repo.bulk_upsert(
            costs=costs,
            connection_id=conn.id,
            provider=conn.provider,
            scan_id=scan_id,
        )
        cost_stale_count = await cost_repo.mark_stale(conn.id, scan_id)

        # ── Compliance: UPSERT + mark stale as deleted ──
        compliance_upserted = await compliance_repo.bulk_upsert(
            compliance=compliance,
            connection_id=conn.id,
            provider=conn.provider,
            scan_id=scan_id,
        )
        compliance_stale_count = await compliance_repo.mark_stale(conn.id, scan_id)

        # ── AI Recommendations: bulk insert + resolve previous open ──
        ai_recs_upserted = 0
        if ai_recommendations:
            ai_recs_upserted = await ai_repo.bulk_insert(
                recommendations=ai_recommendations,
                connection_id=conn.id,
                scan_id=session_record.id,
            )
            # Resolve previous open recommendations so current scan's recs are active
            resolved_count = await ai_repo.resolve_previous_open(conn.id, session_record.id)
            logger.info(
                "recommendations_saved connection_id=%s scan_id=%s recommendation_count=%d previous_resolved=%d",
                str(conn.id), scan_id, ai_recs_upserted, resolved_count,
            )
        else:
            logger.info(
                "recommendations_skipped connection_id=%s scan_id=%s reason=no_recommendations",
                str(conn.id), scan_id,
            )

        # Count active resources for dashboard accuracy
        from sqlalchemy import func as sa_func, select as sa_select

        active_count_result = await db.execute(
            sa_select(sa_func.count(CloudResource.id)).where(
                CloudResource.connection_id == conn.id,
                CloudResource.status == "active",
            )
        )
        active_resource_count = active_count_result.scalar() or 0

        duration = round(time.time() - t0, 2)
        logger.info(
            "PERSIST_COMPLETE",
            connection_id=str(conn.id),
            scan_id=scan_id,
            resources_upserted=resources_upserted,
            resources_skipped=resources_skipped,
            resources_soft_deleted=deleted_count,
            active_resource_count=active_resource_count,
            findings_upserted=findings_upserted,
            findings_skipped=findings_skipped,
            findings_resolved=finding_stale_count,
            costs_upserted=costs_upserted,
            costs_resolved=cost_stale_count,
            compliance_upserted=compliance_upserted,
            compliance_deleted=compliance_stale_count,
            ai_recommendations_upserted=ai_recs_upserted,
            duration_seconds=duration,
        )

        return {
            "resources_upserted": resources_upserted,
            "resources_skipped": resources_skipped,
            "resources_soft_deleted": deleted_count,
            "active_resource_count": active_resource_count,
            "findings_inserted": findings_upserted,
            "findings_skipped": findings_skipped,
            "costs_inserted": costs_upserted,
            "compliance_inserted": compliance_upserted,
            "ai_recommendations_inserted": ai_recs_upserted,
        }

    # ── AI Recommendation helpers ─────────────────────────────────

    @staticmethod
    def _infer_category(service: str) -> str:
        """Infer recommendation category from AWS service name."""
        return SERVICE_CATEGORY.get(service, "security")

    def _ensure_all_findings_have_recs(
        self,
        findings: list[CloudFindingData],
        llm_recs: list[CloudRecommendation],
        connection_id: UUID,
        scan_session_id: UUID,
    ) -> list[CloudRecommendation]:
        """Ensure every finding has at least one recommendation.

        For findings that already have an LLM-generated recommendation, keep it.
        For findings missing one, generate a fallback.
        """
        # Build mapping of which resource_ids already have LLM recs
        covered_resource_ids: set[str] = set()
        for rec in llm_recs:
            if rec.resource_id:
                covered_resource_ids.add(rec.resource_id)

        # Build mapping of which finding_ids already have LLM recs
        covered_finding_ids: set[str] = set()
        for rec in llm_recs:
            if rec.finding_id:
                covered_finding_ids.add(rec.finding_id)

        # Start with all LLM recs
        all_recs = list(llm_recs)

        # Generate fallback for findings without coverage
        for f in findings:
            rid = f.resource_id or ""
            fid = str(rid) or f.title
            if rid in covered_resource_ids or fid in covered_finding_ids:
                continue
            fallback = CloudRecommendation(
                finding_id=fid,
                rule_id=f.rule_id or "",
                service=f.service,
                resource_id=rid,
                region=f.region,
                executive_summary=f"Review and remediate: {f.title}",
                root_cause=f"A {f.severity}-severity issue was detected on {f.service}.",
                business_impact=self._estimate_business_impact(f.severity),
                security_impact=self._estimate_security_impact(f.severity, f.service),
                cost_impact=self._estimate_cost_impact(f.service),
                official_best_practice=f"Follow AWS Well-Architected best practices for {f.service}.",
                terraform_fix=None,
                aws_cli_fix=None,
                cloudformation_fix=None,
                console_steps=[],
                confidence_score=0.5,
                estimated_risk_reduction=30.0 if f.severity in ("critical", "high") else 10.0,
                estimated_monthly_savings=0.0,
                severity=f.severity,
                knowledge_sources_used=["engineered_fallback"],
                llm_provider="engineered",
            )
            all_recs.append(fallback)

        return all_recs

    @staticmethod
    def _recommendation_to_row(
        rec: CloudRecommendation,
        conn: CloudConnection,
        scan_session_id: UUID,
    ) -> dict[str, Any]:
        """Map a CloudRecommendation dataclass to a flat dict for ai_recommendations table."""
        doc_url = ""
        if rec.documentation_references and isinstance(rec.documentation_references, list):
            for ref in rec.documentation_references:
                url = ref.get("url", "") if isinstance(ref, dict) else ""
                if url:
                    doc_url = url
                    break

        # Combine root cause, security impact, cost impact into technical explanation
        parts = [rec.root_cause or ""]
        if rec.security_impact:
            parts.append(f"Security: {rec.security_impact}")
        if rec.cost_impact:
            parts.append(f"Cost: {rec.cost_impact}")
        tech_explanation = "\n\n".join(p for p in parts if p)

        # Truncate executive_summary to first ~120 chars for title
        title = (rec.executive_summary or rec.root_cause or rec.service)[:120]

        source = "ai_generated" if rec.llm_provider and rec.llm_provider != "engineered" else "engineered"

        return {
            "provider": conn.provider,
            "service": rec.service,
            "resource_id": rec.resource_id,
            "resource_name": "",
            "category": SERVICE_CATEGORY.get(rec.service, "security"),
            "severity": rec.severity,
            "title": title,
            "summary": rec.executive_summary or "",
            "technical_explanation": tech_explanation,
            "business_impact": rec.business_impact or "",
            "estimated_monthly_savings": rec.estimated_monthly_savings or 0.0,
            "estimated_risk_reduction": rec.estimated_risk_reduction or 0.0,
            "aws_cli_fix": rec.aws_cli_fix,
            "terraform_fix": rec.terraform_fix,
            "cloudformation_fix": rec.cloudformation_fix,
            "console_steps": rec.console_steps or [],
            "official_documentation_url": doc_url or None,
            "recommendation_source": source,
        }

    @staticmethod
    def _estimate_business_impact(severity: str) -> str:
        impacts = {
            "critical": "Immediate risk of data breach, service outage, or compliance violation.",
            "high": "Significant security or operational risk if not addressed within 7 days.",
            "medium": "Moderate risk that should be addressed within 30 days.",
            "low": "Minor improvement opportunity with minimal immediate risk.",
        }
        return impacts.get(severity, "Impact assessment required.")

    @staticmethod
    def _estimate_security_impact(severity: str, service: str) -> str:
        impacts = {
            "critical": f"Critical {service} security gap — potential for unauthorized access or data exposure.",
            "high": f"High-severity {service} issue — could be exploited to escalate privileges or access data.",
            "medium": f"Medium-severity {service} finding — violates security best practices.",
            "low": f"Low-severity {service} observation — minor deviation from best practices.",
        }
        return impacts.get(severity, "Security impact assessment required.")

    @staticmethod
    def _estimate_cost_impact(service: str) -> str:
        return f"Review {service} resource utilization and pricing model for optimization opportunities."

    def _compute_compliance(self, findings: list[CloudFindingData]) -> list[dict[str, Any]]:
        frameworks = ["AWS Foundational Security", "CIS AWS Foundations", "NIST 800-53"]
        results: list[dict[str, Any]] = []
        for fw in frameworks:
            fw_findings = [f for f in findings if fw.lower() in " ".join(f.compliance_frameworks).lower()]
            total = max(len(fw_findings), 1)
            failed = len([f for f in fw_findings if f.severity in ("critical", "high")])
            passed = total - failed
            score = round((passed / total) * 100, 1) if total > 0 else 100.0
            results.append({
                "framework": fw,
                "total_controls": total,
                "passed": passed,
                "failed": failed,
                "warnings": 0,
                "not_applicable": 0,
                "score": score,
                "details": {},
            })
        return results

    def _compute_security_score(self, findings: list[CloudFindingData]) -> float:
        if not findings:
            return 100.0
        weights = {"critical": 25, "high": 15, "medium": 5, "low": 1}
        penalty = sum(weights.get(f.severity, 0) for f in findings)
        return max(0.0, round(100.0 - penalty, 1))


cloud_scan_orchestrator = CloudScanOrchestrator()
