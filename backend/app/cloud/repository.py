"""Repository layer for cloud resource persistence.

Responsibilities:
  - Accept DTOs from scanners
  - Sanitize JSON fields (configuration, tags, evidence, etc.)
  - Normalize timestamps to UTC
  - Batch insert/upsert into PostgreSQL
  - Handle errors per-resource (log + skip, never fail entire scan)
  - Scan-based soft-deletion: each scan stamps last_scan_id, stale resources
    are marked deleted by comparing last_scan_id (scales to millions of resources)

No scanner should use SQLAlchemy directly. All persistence goes through
these repositories.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.cloud.base import (
    CloudCostData,
    CloudFindingData,
    CloudResourceData,
    CloudResourceDTO,
    normalize_timestamp,
    sanitize_json,
)
from app.models.ai_recommendation import AIRecommendation
from app.models.cloud import (
    CloudComplianceResult,
    CloudCostRecommendation,
    CloudFinding,
    CloudResource,
)

logger = logging.getLogger(__name__)

# Batch size for bulk inserts — balance between memory and round-trips.
BATCH_SIZE = 500


# ─── Resource Repository ───────────────────────────────────────────

class CloudResourceRepository:
    """Handles persistence for cloud resources.

    Unique key for upsert: (connection_id, provider, region, resource_id)
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _resource_to_row(
        dto: CloudResourceDTO,
        connection_id: UUID,
        scan_id: str,
    ) -> dict[str, Any]:
        """Convert a CloudResourceDTO to a dict suitable for INSERT/UPDATE.

        Sanitizes JSON fields and normalizes timestamps before the row
        ever touches SQLAlchemy.
        """
        return {
            "connection_id": connection_id,
            "provider": dto.provider,
            "account_id": dto.account_id,
            "service": dto.service,
            "resource_id": dto.resource_id,
            "resource_name": dto.resource_name,
            "resource_type": dto.resource_type,
            "region": dto.region,
            "status": dto.status,
            "configuration": sanitize_json(dto.configuration) if dto.configuration else {},
            "tags": sanitize_json(dto.tags) if dto.tags else {},
            "cost_monthly": dto.cost_monthly,
            "created_at": normalize_timestamp(dto.created_at),
            "last_modified_at": normalize_timestamp(dto.last_modified_at),
            "last_scan_id": scan_id,
        }

    @staticmethod
    def _legacy_resource_to_row(
        r: CloudResourceData,
        connection_id: UUID,
        account_id: str,
        scan_id: str,
    ) -> dict[str, Any]:
        """Convert legacy CloudResourceData dataclass to a sanitized row dict.

        This bridges existing scanners that return CloudResourceData instead
        of CloudResourceDTO. The orchestrator should prefer DTOs for new code.
        """
        return {
            "connection_id": connection_id,
            "provider": r.provider,
            "account_id": account_id,
            "service": r.service,
            "resource_id": r.resource_id,
            "resource_name": r.resource_name,
            "resource_type": r.resource_type,
            "region": r.region,
            "status": r.status,
            "configuration": sanitize_json(r.configuration) if r.configuration else {},
            "tags": sanitize_json(r.tags) if r.tags else {},
            "cost_monthly": r.cost_monthly,
            "created_at": normalize_timestamp(r.created_at),
            "last_modified_at": normalize_timestamp(r.last_modified_at),
            "last_scan_id": scan_id,
        }

    async def bulk_upsert(
        self,
        resources: list[CloudResourceDTO],
        connection_id: UUID,
        scan_id: str,
        batch_size: int = BATCH_SIZE,
    ) -> tuple[int, int, list[dict[str, str]]]:
        """Upsert resources in batches. Returns (inserted, skipped, errors).

        Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE for each batch.
        Unique key: (connection_id, provider, region, resource_id).

        If one resource fails validation, it is logged and skipped.
        Never fails the entire scan.
        """
        t0 = time.time()
        rows = []
        errors: list[dict[str, str]] = []

        for dto in resources:
            try:
                rows.append(self._resource_to_row(dto, connection_id, scan_id))
            except Exception as exc:
                errors.append({
                    "resource_id": dto.resource_id,
                    "resource_type": dto.resource_type,
                    "service": dto.service,
                    "error": str(exc),
                })
                logger.warning(
                    "RESOURCE_VALIDATION_FAILED resource_id=%s resource_type=%s service=%s error=%s",
                    dto.resource_id, dto.resource_type, dto.service, str(exc),
                )

        inserted = await self._execute_upsert_batch(rows, batch_size)
        duration = round(time.time() - t0, 2)
        logger.info(
            "RESOURCE_UPSERT_COMPLETE total=%d inserted=%d skipped=%d duration_seconds=%.2f",
            len(resources), inserted, len(errors), duration,
        )
        return inserted, len(errors), errors

    async def bulk_upsert_legacy(
        self,
        resources: list[CloudResourceData],
        connection_id: UUID,
        account_id: str,
        scan_id: str,
        batch_size: int = BATCH_SIZE,
    ) -> tuple[int, int, list[dict[str, str]]]:
        """Upsert legacy CloudResourceData instances. Returns (inserted, skipped, errors).

        Same as bulk_upsert but accepts the old dataclass format.
        """
        t0 = time.time()
        rows = []
        errors: list[dict[str, str]] = []

        for r in resources:
            try:
                rows.append(self._legacy_resource_to_row(r, connection_id, account_id, scan_id))
            except Exception as exc:
                errors.append({
                    "resource_id": r.resource_id,
                    "resource_type": r.resource_type,
                    "service": r.service,
                    "error": str(exc),
                })
                logger.warning(
                    "RESOURCE_VALIDATION_FAILED resource_id=%s resource_type=%s service=%s error=%s",
                    r.resource_id, r.resource_type, r.service, str(exc),
                )

        inserted = await self._execute_upsert_batch(rows, batch_size)
        duration = round(time.time() - t0, 2)
        logger.info(
            "RESOURCE_UPSERT_COMPLETE total=%d inserted=%d skipped=%d duration_seconds=%.2f",
            len(resources), inserted, len(errors), duration,
        )
        return inserted, len(errors), errors

    async def _execute_upsert_batch(
        self,
        rows: list[dict[str, Any]],
        batch_size: int,
    ) -> int:
        """Execute upsert in batches. Returns total inserted count."""
        total_inserted = 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            if not batch:
                continue
            try:
                stmt = pg_insert(CloudResource).values(batch)
                update_cols = {
                    col.name: col
                    for col in stmt.excluded
                    if col.name not in ("id", "connection_id", "created_at")
                }
                stmt = stmt.on_conflict_do_update(
                    index_elements=["connection_id", "provider", "region", "resource_id"],
                    set_=update_cols,
                )
                result = await self.db.execute(stmt)
                # Detailed logging for this batch
                batch_inserted = result.rowcount
                total_inserted += batch_inserted
                for row in batch:
                    logger.debug(
                        "RESOURCE_UPSERTED: service=%s region=%s resource_id=%s resource_type=%s status=%s",
                        row.get("service", "?"),
                        row.get("region", "?"),
                        row.get("resource_id", "?"),
                        row.get("resource_type", "?"),
                        row.get("status", "?"),
                    )
            except Exception as exc:
                logger.error(
                    "RESOURCE_BATCH_UPSERT_FAILED batch_start=%d batch_size=%d error=%s",
                    i, len(batch), str(exc),
                )
                raise
        return total_inserted

    async def delete_stale(
        self,
        connection_id: UUID,
        scan_id: str,
    ) -> int:
        """Soft-delete resources not seen in the current scan.

        Instead of passing a huge NOT IN list, we compare last_scan_id.
        Resources where last_scan_id != current scan_id are marked as deleted.
        This scales to millions of resources.

        Pre-conditions:
          - bulk_upsert / bulk_upsert_legacy has already been called with scan_id
          - All upserted resources now have last_scan_id == scan_id
        """
        # First, log which resources are about to be marked deleted
        stale_query = select(
            CloudResource.id, CloudResource.service, CloudResource.region,
            CloudResource.resource_id, CloudResource.resource_type,
        ).where(
            CloudResource.connection_id == connection_id,
            CloudResource.last_scan_id != scan_id,
            CloudResource.status != "deleted",
        )
        stale_resources = await self.db.execute(stale_query)
        stale_list = list(stale_resources)
        for r in stale_list:
            logger.info(
                "RESOURCE_MARKED_DELETED: connection_id=%s service=%s region=%s resource_id=%s resource_type=%s",
                str(connection_id), r.service, r.region, r.resource_id, r.resource_type,
            )

        result = await self.db.execute(
            update(CloudResource)
            .where(
                CloudResource.connection_id == connection_id,
                CloudResource.last_scan_id != scan_id,
                CloudResource.status != "deleted",
            )
            .values(status="deleted", scanned_at=func.now())
        )
        deleted_count = result.rowcount

        if deleted_count > 0:
            logger.info(
                "RESOURCES_SOFT_DELETED: connection_id=%s scan_id=%s deleted_count=%d",
                str(connection_id), scan_id, deleted_count,
            )
        else:
            logger.info(
                "RESOURCES_SOFT_DELETED: connection_id=%s scan_id=%s deleted_count=0 (no stale resources)",
                str(connection_id), scan_id,
            )
        return deleted_count


# ─── Finding Repository ────────────────────────────────────────────

class CloudFindingRepository:
    """Handles persistence for cloud security findings.

    Unique key for upsert: (connection_id, provider, service, region, resource_id, rule_id)
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _finding_to_row(
        f: CloudFindingData,
        connection_id: UUID,
        provider: str,
        scan_id: str,
    ) -> dict[str, Any]:
        return {
            "connection_id": connection_id,
            "provider": provider,
            "service": f.service,
            "category": f.category,
            "severity": f.severity,
            "title": f.title,
            "description": f.description,
            "resource_id": f.resource_id or "",
            "resource_type": f.resource_type,
            "region": f.region,
            "rule_id": f.rule_id or "",
            "compliance_frameworks": sanitize_json(f.compliance_frameworks),
            "remediation": f.remediation,
            "remediation_url": f.remediation_url,
            "evidence": sanitize_json(f.evidence) if f.evidence else {},
            "last_scan_id": scan_id,
            "status": "open",
        }

    async def bulk_upsert(
        self,
        findings: list[CloudFindingData],
        connection_id: UUID,
        provider: str,
        scan_id: str,
        batch_size: int = BATCH_SIZE,
    ) -> tuple[int, int, list[dict[str, str]]]:
        """Upsert findings in batches. Returns (inserted, skipped, errors)."""
        t0 = time.time()
        rows = []
        errors: list[dict[str, str]] = []

        for f in findings:
            try:
                rows.append(self._finding_to_row(f, connection_id, provider, scan_id))
            except Exception as exc:
                errors.append({
                    "rule_id": f.rule_id or "unknown",
                    "resource_id": f.resource_id or "unknown",
                    "service": f.service,
                    "error": str(exc),
                })
                logger.warning(
                    "FINDING_VALIDATION_FAILED rule_id=%s resource_id=%s error=%s",
                    f.rule_id, f.resource_id, str(exc),
                )

        total_upserted = 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            if not batch:
                continue
            # Deduplicate by unique key — ON CONFLICT DO UPDATE rejects
            # rows with duplicate constrained values in the same statement.
            dedup: dict[tuple, dict] = {}
            for r in batch:
                key = (r["connection_id"], r["provider"], r["service"],
                       r["region"], r["resource_id"], r["rule_id"])
                dedup[key] = r
            batch = list(dedup.values())
            try:
                stmt = pg_insert(CloudFinding).values(batch)
                update_cols = {
                    col.name: col
                    for col in stmt.excluded
                    if col.name not in ("id", "connection_id", "created_at")
                }
                stmt = stmt.on_conflict_do_update(
                    index_elements=[
                        "connection_id", "provider", "service", "region",
                        "resource_id", "rule_id",
                    ],
                    set_=update_cols,
                )
                result = await self.db.execute(stmt)
                total_upserted += result.rowcount
            except Exception as exc:
                logger.error(
                    "FINDING_BATCH_UPSERT_FAILED batch_start=%d batch_size=%d error=%s",
                    i, len(batch), str(exc),
                )
                raise

        duration = round(time.time() - t0, 2)
        logger.info(
            "FINDING_UPSERT_COMPLETE total=%d upserted=%d skipped=%d duration_seconds=%.2f",
            len(findings), total_upserted, len(errors), duration,
        )
        return total_upserted, len(errors), errors

    async def mark_stale(
        self,
        connection_id: UUID,
        scan_id: str,
    ) -> int:
        """Mark findings not seen in the current scan as 'resolved'.

        Uses last_scan_id comparison to find findings from previous scans
        that are no longer active. Sets status='resolved' so they are
        preserved for history but excluded from active dashboards.
        """
        stale_query = select(
            CloudFinding.id, CloudFinding.service, CloudFinding.resource_id,
            CloudFinding.region, CloudFinding.rule_id,
        ).where(
            CloudFinding.connection_id == connection_id,
            CloudFinding.last_scan_id != scan_id,
            CloudFinding.status.in_(["open", "in_progress"]),
        )
        stale_findings = await self.db.execute(stale_query)
        stale_list = list(stale_findings)
        for f in stale_list:
            logger.info(
                "FINDING_MARKED_RESOLVED: connection_id=%s service=%s region=%s resource_id=%s rule_id=%s",
                str(connection_id), f.service, f.region, f.resource_id, f.rule_id,
            )

        result = await self.db.execute(
            update(CloudFinding)
            .where(
                CloudFinding.connection_id == connection_id,
                CloudFinding.last_scan_id != scan_id,
                CloudFinding.status.in_(["open", "in_progress"]),
            )
            .values(status="resolved", updated_at=func.now())
        )
        resolved_count = result.rowcount

        if resolved_count > 0:
            logger.info(
                "FINDINGS_MARKED_RESOLVED: connection_id=%s scan_id=%s count=%d",
                str(connection_id), scan_id, resolved_count,
            )
        else:
            logger.info(
                "FINDINGS_MARKED_RESOLVED: connection_id=%s scan_id=%s count=0 (no stale findings)",
                str(connection_id), scan_id,
            )
        return resolved_count


# ─── Cost Recommendation Repository ────────────────────────────────

class CloudCostRepository:
    """Handles persistence for cloud cost recommendations.

    Unique key for upsert: (connection_id, provider, service, region, resource_id, recommendation_type)
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _cost_to_row(
        c: CloudCostData,
        connection_id: UUID,
        provider: str,
        scan_id: str,
    ) -> dict[str, Any]:
        return {
            "connection_id": connection_id,
            "provider": provider,
            "service": c.service,
            "title": c.title,
            "description": c.description,
            "resource_id": c.resource_id or "",
            "resource_type": c.resource_type,
            "region": c.region,
            "monthly_savings": c.monthly_savings,
            "current_cost": c.current_cost,
            "priority": c.priority,
            "category": c.category,
            "recommendation_type": c.recommendation_type,
            "estimated_impact": c.estimated_impact,
            "last_scan_id": scan_id,
            "status": "open",
        }

    async def bulk_upsert(
        self,
        costs: list[CloudCostData],
        connection_id: UUID,
        provider: str,
        scan_id: str,
        batch_size: int = BATCH_SIZE,
    ) -> int:
        """Upsert cost recommendations in batches."""
        t0 = time.time()
        rows = [self._cost_to_row(c, connection_id, provider, scan_id) for c in costs]

        total = 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            if not batch:
                continue
            try:
                stmt = pg_insert(CloudCostRecommendation).values(batch)
                update_cols = {
                    col.name: col
                    for col in stmt.excluded
                    if col.name not in ("id", "connection_id", "created_at")
                }
                stmt = stmt.on_conflict_do_update(
                    index_elements=[
                        "connection_id", "provider", "service", "region",
                        "resource_id", "recommendation_type",
                    ],
                    set_=update_cols,
                )
                result = await self.db.execute(stmt)
                total += result.rowcount
            except Exception as exc:
                logger.error(
                    "COST_BATCH_UPSERT_FAILED batch_start=%d batch_size=%d error=%s",
                    i, len(batch), str(exc),
                )
                raise

        duration = round(time.time() - t0, 2)
        logger.info("COST_UPSERT_COMPLETE upserted=%d duration_seconds=%.2f", total, duration)
        return total

    async def mark_stale(
        self,
        connection_id: UUID,
        scan_id: str,
    ) -> int:
        """Mark cost recommendations not seen in the current scan as 'resolved'."""
        stale_query = select(
            CloudCostRecommendation.id, CloudCostRecommendation.service,
            CloudCostRecommendation.resource_id, CloudCostRecommendation.recommendation_type,
        ).where(
            CloudCostRecommendation.connection_id == connection_id,
            CloudCostRecommendation.last_scan_id != scan_id,
            CloudCostRecommendation.status == "open",
        )
        stale_recs = await self.db.execute(stale_query)
        for r in list(stale_recs):
            logger.info(
                "COST_MARKED_RESOLVED: connection_id=%s service=%s resource_id=%s type=%s",
                str(connection_id), r.service, r.resource_id, r.recommendation_type,
            )

        result = await self.db.execute(
            update(CloudCostRecommendation)
            .where(
                CloudCostRecommendation.connection_id == connection_id,
                CloudCostRecommendation.last_scan_id != scan_id,
                CloudCostRecommendation.status == "open",
            )
            .values(status="resolved")
        )
        resolved_count = result.rowcount
        logger.info(
            "COST_MARKED_RESOLVED: connection_id=%s scan_id=%s count=%d",
            str(connection_id), scan_id, resolved_count,
        )
        return resolved_count


# ─── Compliance Result Repository ──────────────────────────────────

class CloudComplianceRepository:
    """Handles persistence for compliance results.

    Unique key for upsert: (connection_id, provider, framework)
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def bulk_upsert(
        self,
        compliance: list[dict[str, Any]],
        connection_id: UUID,
        provider: str,
        scan_id: str,
    ) -> int:
        """Upsert compliance results."""
        rows = [
            {
                "connection_id": connection_id,
                "provider": provider,
                "framework": comp["framework"],
                "total_controls": comp["total_controls"],
                "passed": comp["passed"],
                "failed": comp["failed"],
                "warnings": comp.get("warnings", 0),
                "not_applicable": comp.get("not_applicable", 0),
                "score": comp["score"],
                "details": sanitize_json(comp.get("details", {})),
                "last_scan_id": scan_id,
                "status": "active",
            }
            for comp in compliance
        ]

        if not rows:
            return 0

        stmt = pg_insert(CloudComplianceResult).values(rows)
        update_cols = {
            col.name: col
            for col in stmt.excluded
            if col.name not in ("id", "connection_id", "created_at")
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["connection_id", "provider", "framework"],
            set_=update_cols,
        )
        result = await self.db.execute(stmt)
        inserted = result.rowcount
        logger.info("COMPLIANCE_UPSERT_COMPLETE upserted=%d", inserted)
        return inserted

    async def mark_stale(
        self,
        connection_id: UUID,
        scan_id: str,
    ) -> int:
        """Mark compliance results not seen in the current scan as 'deleted'."""
        result = await self.db.execute(
            update(CloudComplianceResult)
            .where(
                CloudComplianceResult.connection_id == connection_id,
                CloudComplianceResult.last_scan_id != scan_id,
                CloudComplianceResult.status == "active",
            )
            .values(status="deleted")
        )
        deleted_count = result.rowcount
        if deleted_count > 0:
            logger.info(
                "COMPLIANCE_MARKED_DELETED: connection_id=%s scan_id=%s count=%d",
                str(connection_id), scan_id, deleted_count,
            )
        return deleted_count


# ─── AI Recommendation Repository ──────────────────────────────────

class AIRecommendationRepository:
    """Handles persistence for AI-generated recommendations.

    No upsert complexity — each finding generates one or more rows.
    Old recommendations are soft-deleted by marking status='resolved'
    (not via last_scan_id; we use scan_id tracking instead).
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def bulk_insert(
        self,
        recommendations: list[dict[str, Any]],
        connection_id: UUID,
        scan_id: UUID | None,
        batch_size: int = BATCH_SIZE,
    ) -> int:
        """Bulk insert AI recommendations. No conflict handling — each is distinct."""
        rows = []
        for rec in recommendations:
            rows.append({
                "connection_id": connection_id,
                "scan_id": scan_id,
                "provider": rec.get("provider", "aws"),
                "service": rec.get("service", ""),
                "resource_id": rec.get("resource_id", ""),
                "resource_name": rec.get("resource_name", ""),
                "category": rec.get("category", "security"),
                "severity": rec.get("severity", "medium"),
                "title": rec.get("title", ""),
                "summary": rec.get("summary", ""),
                "technical_explanation": rec.get("technical_explanation", ""),
                "business_impact": rec.get("business_impact", ""),
                "estimated_monthly_savings": rec.get("estimated_monthly_savings", 0.0),
                "estimated_risk_reduction": rec.get("estimated_risk_reduction", 0.0),
                "aws_cli_fix": rec.get("aws_cli_fix"),
                "terraform_fix": rec.get("terraform_fix"),
                "cloudformation_fix": rec.get("cloudformation_fix"),
                "console_steps": sanitize_json(rec.get("console_steps", [])),
                "official_documentation_url": rec.get("official_documentation_url"),
                "recommendation_source": rec.get("recommendation_source", "ai_generated"),
                "status": "open",
            })

        total = 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            if not batch:
                continue
            try:
                stmt = pg_insert(AIRecommendation).values(batch)
                result = await self.db.execute(stmt)
                total += result.rowcount
            except Exception as exc:
                logger.error(
                    "AI_RECOMMENDATION_BATCH_INSERT_FAILED batch_start=%d batch_size=%d error=%s",
                    i, len(batch), str(exc),
                )
                raise

        logger.info(
            "AI_RECOMMENDATION_BULK_INSERT connection_id=%s scan_id=%s count=%d",
            str(connection_id), str(scan_id), total,
        )
        return total

    async def resolve_previous_open(
        self,
        connection_id: UUID,
        scan_id: UUID | None,
    ) -> int:
        """Mark previously open recommendations as 'resolved' for a new scan.

        Returns count of rows updated.
        """
        result = await self.db.execute(
            update(AIRecommendation)
            .where(
                AIRecommendation.connection_id == connection_id,
                AIRecommendation.status == "open",
            )
            .values(
                status="resolved",
                updated_at=func.now(),
            )
        )
        count = result.rowcount or 0
        if count > 0:
            logger.info(
                "AI_RECOMMENDATIONS_RESOLVED connection_id=%s scan_id=%s count=%d",
                str(connection_id), str(scan_id), count,
            )
        return count

    async def count_by_connection(
        self,
        connection_id: UUID,
        status: str | None = None,
    ) -> int:
        """Count recommendations for a connection, optionally filtered by status."""
        from sqlalchemy import func as sa_func, select as sa_select

        stmt = sa_select(sa_func.count(AIRecommendation.recommendation_id)).where(
            AIRecommendation.connection_id == connection_id,
        )
        if status:
            stmt = stmt.where(AIRecommendation.status == status)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_summary(
        self,
        connection_id: UUID,
    ) -> dict[str, Any]:
        """Aggregate summary for the overview dashboard — single query."""
        from sqlalchemy import func as sa_func, select as sa_select

        rows_result = await self.db.execute(
            sa_select(
                AIRecommendation.severity,
                AIRecommendation.category,
                AIRecommendation.status,
                sa_func.count().label("cnt"),
                sa_func.coalesce(sa_func.sum(AIRecommendation.estimated_monthly_savings), 0).label("total_savings"),
                sa_func.coalesce(sa_func.avg(AIRecommendation.estimated_risk_reduction), 0).label("avg_risk"),
            ).where(
                AIRecommendation.connection_id == connection_id,
            ).group_by(
                AIRecommendation.severity,
                AIRecommendation.category,
                AIRecommendation.status,
            )
        )
        aggs = rows_result.all()

        by_severity: dict[str, int] = {}
        by_category: dict[str, int] = {}
        by_status: dict[str, int] = {}
        total_savings = 0.0
        total_risk = 0.0
        total_count = 0
        critical_count = 0

        for row in aggs:
            sev = row.severity or "unknown"
            cat = row.category or "unknown"
            st = row.status or "open"
            cnt = row.cnt or 0
            by_severity[sev] = by_severity.get(sev, 0) + cnt
            by_category[cat] = by_category.get(cat, 0) + cnt
            by_status[st] = by_status.get(st, 0) + cnt
            total_count += cnt
            total_savings += float(row.total_savings or 0)
            total_risk += float(row.avg_risk or 0) * cnt
            if sev == "critical":
                critical_count += cnt

        total_savings = round(total_savings, 2)
        total_risk = round(total_risk / max(total_count, 1), 1)

        return {
            "total": total_count,
            "by_severity": by_severity,
            "by_category": by_category,
            "by_status": by_status,
            "total_monthly_savings": total_savings,
            "avg_risk_reduction": total_risk,
            "critical_count": critical_count,
        }


# ─── Aggregate Stats Repository ────────────────────────────────────

class CloudConnectionStatsRepository:
    """Updates aggregate stats on cloud_connections after a scan."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def update_after_scan(
        self,
        connection_id: UUID,
        resource_count: int,
        finding_count: int,
        security_score: float,
        estimated_monthly_cost: float,
    ) -> None:
        """Update the connection's aggregate counters."""
        from sqlalchemy import update

        from app.models.cloud import CloudConnection

        await self.db.execute(
            update(CloudConnection)
            .where(CloudConnection.id == connection_id)
            .values(
                resource_count=resource_count,
                finding_count=finding_count,
                security_score=security_score,
                estimated_monthly_cost=estimated_monthly_cost,
            )
        )
