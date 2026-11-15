"""Integration tests for cloud scan lifecycle — UPSERT, soft-delete, and dashboard accuracy.

Tests the full persistence pipeline:
  - Resource UPSERT with duplicate prevention
  - Resource stale detection (soft-delete via last_scan_id)
  - Finding UPSERT + mark_stale (status -> resolved)
  - Cost recommendation UPSERT + mark_stale
  - Compliance UPSERT + mark_stale
  - Dashboard count accuracy (only active resources counted)
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func as sa_func, select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.cloud.base import CloudCostData, CloudFindingData, CloudResourceData
from app.cloud.repository import (
    AIRecommendationRepository,
    CloudComplianceRepository,
    CloudCostRepository,
    CloudFindingRepository,
    CloudResourceRepository,
)
from app.db.base import Base
from app.models.ai_recommendation import AIRecommendation
from app.models.cloud import (
    CloudComplianceResult,
    CloudConnection,
    CloudCostRecommendation,
    CloudFinding,
    CloudResource,
)

# ---------------------------------------------------------------------------
# Fixtures — isolated TEST_DATABASE_URL (docker-compose.test.yml)
# ---------------------------------------------------------------------------

from tests.db_test_config import get_test_async_database_url

TEST_DB_URL = get_test_async_database_url()


@pytest.fixture(scope="function")
async def engine():
    engine = create_async_engine(TEST_DB_URL, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.execute(sa_text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def db(engine):
    """Fresh session for each test with rollback at the end."""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture()
async def connection(db: AsyncSession) -> CloudConnection:
    from sqlalchemy import text as sa_text

    user_id = uuid.uuid4()
    # Insert minimal user to satisfy FK constraint
    await db.execute(
        sa_text("""
            INSERT INTO users (id, email_encrypted, email_hash, username, hashed_password, is_active, is_verified, role, subscription_plan, subscription_status, mfa_enabled, failed_login_attempts)
            VALUES (:id, '', '', 'test-user', '', true, false, 'USER', 'free', 'active', false, 0)
        """),
        {"id": user_id},
    )
    conn = CloudConnection(
        id=uuid.uuid4(),
        user_id=user_id,
        provider="aws",
        account_id="123456789012",
        connection_name="test-connection",
        role_arn="arn:aws:iam::123456789012:role/DevArchAI-Scanner",
    )
    db.add(conn)
    await db.flush()
    return conn


@pytest.fixture()
def scan_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture()
def scan_id_2() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Resource lifecycle tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.requires_db
class TestResourceLifecycle:
    """Test resource UPSERT, duplicate prevention, and stale soft-delete."""

    async def test_upsert_new_resources(self, db, connection, scan_id):
        repo = CloudResourceRepository(db)
        resources = [
            CloudResourceData(
                provider="aws", service="ec2", resource_id="i-123",
                resource_name="web-server", resource_type="instance",
                region="us-east-1", status="running",
            ),
            CloudResourceData(
                provider="aws", service="ec2", resource_id="i-456",
                resource_name="db-server", resource_type="instance",
                region="us-east-1", status="stopped",
            ),
        ]
        inserted, skipped, errors = await repo.bulk_upsert_legacy(
            resources=resources,
            connection_id=connection.id,
            account_id=connection.account_id,
            scan_id=scan_id,
        )
        assert inserted == 2
        assert skipped == 0
        assert errors == []

        # Verify both resources exist
        result = await db.execute(
            select(CloudResource).where(CloudResource.connection_id == connection.id)
        )
        rows = result.scalars().all()
        assert len(rows) == 2

    async def test_upsert_duplicate_updates_existing(self, db, connection, scan_id):
        repo = CloudResourceRepository(db)
        resources = [
            CloudResourceData(
                provider="aws", service="ec2", resource_id="i-123",
                resource_name="web-server", resource_type="instance",
                region="us-east-1", status="running",
            ),
        ]
        await repo.bulk_upsert_legacy(
            resources=resources, connection_id=connection.id,
            account_id=connection.account_id, scan_id=scan_id,
        )

        # Same resource_id but updated status
        resources[0].status = "stopped"
        inserted, skipped, errors = await repo.bulk_upsert_legacy(
            resources=resources, connection_id=connection.id,
            account_id=connection.account_id, scan_id=scan_id,
        )
        assert inserted >= 1  # PostgreSQL returns 1 for update
        assert skipped == 0

        result = await db.execute(
            select(CloudResource).where(
                CloudResource.connection_id == connection.id,
                CloudResource.resource_id == "i-123",
            )
        )
        row = result.scalar_one()
        assert row.status == "stopped"

    async def test_upsert_different_regions_are_distinct(self, db, connection, scan_id):
        repo = CloudResourceRepository(db)
        resources = [
            CloudResourceData(
                provider="aws", service="ec2", resource_id="i-123",
                resource_name="web", resource_type="instance",
                region="us-east-1", status="running",
            ),
            CloudResourceData(
                provider="aws", service="ec2", resource_id="i-123",
                resource_name="web-eu", resource_type="instance",
                region="eu-west-1", status="running",
            ),
        ]
        inserted, _, _ = await repo.bulk_upsert_legacy(
            resources=resources, connection_id=connection.id,
            account_id=connection.account_id, scan_id=scan_id,
        )
        assert inserted == 2

    async def test_stale_resources_marked_deleted(self, db, connection, scan_id, scan_id_2):
        repo = CloudResourceRepository(db)
        resources_scan1 = [
            CloudResourceData(
                provider="aws", service="ec2", resource_id="i-keep",
                resource_name="keep", resource_type="instance",
                region="us-east-1", status="running",
            ),
            CloudResourceData(
                provider="aws", service="ec2", resource_id="i-stale",
                resource_name="stale", resource_type="instance",
                region="us-east-1", status="running",
            ),
        ]
        await repo.bulk_upsert_legacy(
            resources=resources_scan1, connection_id=connection.id,
            account_id=connection.account_id, scan_id=scan_id,
        )

        # Scan 2: only i-keep is present
        resources_scan2 = [
            CloudResourceData(
                provider="aws", service="ec2", resource_id="i-keep",
                resource_name="keep", resource_type="instance",
                region="us-east-1", status="running",
            ),
        ]
        await repo.bulk_upsert_legacy(
            resources=resources_scan2, connection_id=connection.id,
            account_id=connection.account_id, scan_id=scan_id_2,
        )
        deleted = await repo.delete_stale(connection.id, scan_id_2)
        assert deleted == 1  # i-stale should be marked deleted

        # Verify i-keep is still active, i-stale is deleted
        result = await db.execute(
            select(CloudResource).where(
                CloudResource.connection_id == connection.id,
            )
        )
        rows = {r.resource_id: r.status for r in result.scalars().all()}
        assert rows["i-keep"] == "running"
        assert rows["i-stale"] == "deleted"

    async def test_dashboard_counts_only_active(self, db, connection, scan_id, scan_id_2):
        repo = CloudResourceRepository(db)
        resources_scan1 = [
            CloudResourceData(
                provider="aws", service="ec2", resource_id="a", resource_name="a",
                resource_type="instance", region="us-east-1", status="running",
            ),
            CloudResourceData(
                provider="aws", service="ec2", resource_id="b", resource_name="b",
                resource_type="instance", region="us-east-1", status="running",
            ),
            CloudResourceData(
                provider="aws", service="s3", resource_id="bucket1", resource_name="b1",
                resource_type="bucket", region="us-east-1", status="available",
            ),
        ]
        await repo.bulk_upsert_legacy(
            resources=resources_scan1, connection_id=connection.id,
            account_id=connection.account_id, scan_id=scan_id,
        )

        # Scan 2: only one resource remains
        resources_scan2 = [
            CloudResourceData(
                provider="aws", service="ec2", resource_id="a", resource_name="a",
                resource_type="instance", region="us-east-1", status="running",
            ),
        ]
        await repo.bulk_upsert_legacy(
            resources=resources_scan2, connection_id=connection.id,
            account_id=connection.account_id, scan_id=scan_id_2,
        )
        await repo.delete_stale(connection.id, scan_id_2)

        # Active count should be 1 (status != "deleted")
        result = await db.execute(
            select(sa_func.count(CloudResource.id)).where(
                CloudResource.connection_id == connection.id,
                CloudResource.status != "deleted",
            )
        )
        assert result.scalar() == 1


# ---------------------------------------------------------------------------
# Finding lifecycle tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.requires_db
class TestFindingLifecycle:
    """Test finding UPSERT, duplicate prevention, and stale -> resolved."""

    async def test_upsert_findings(self, db, connection, scan_id):
        repo = CloudFindingRepository(db)
        findings = [
            CloudFindingData(
                provider="aws", service="ec2", category="security",
                severity="high", title="SGRule-001", description="Open SSH",
                resource_id="sg-123", region="us-east-1", rule_id="EC2-SSH-OPEN",
            ),
        ]
        upserted, skipped, errors = await repo.bulk_upsert(
            findings=findings, connection_id=connection.id,
            provider=connection.provider, scan_id=scan_id,
        )
        assert upserted == 1

    async def test_upsert_duplicate_finding_updates(self, db, connection, scan_id):
        repo = CloudFindingRepository(db)
        finding = CloudFindingData(
            provider="aws", service="ec2", category="security",
            severity="high", title="SGRule-001", description="Open SSH",
            resource_id="sg-123", region="us-east-1", rule_id="EC2-SSH-OPEN",
        )
        await repo.bulk_upsert(
            findings=[finding], connection_id=connection.id,
            provider=connection.provider, scan_id=scan_id,
        )

        # Same finding with updated severity
        finding.severity = "critical"
        upserted, _, _ = await repo.bulk_upsert(
            findings=[finding], connection_id=connection.id,
            provider=connection.provider, scan_id=scan_id,
        )
        assert upserted >= 1

        result = await db.execute(
            select(CloudFinding).where(
                CloudFinding.connection_id == connection.id,
                CloudFinding.rule_id == "EC2-SSH-OPEN",
            )
        )
        row = result.scalar_one()
        assert row.severity == "critical"
        assert row.status == "open"

    async def test_mark_stale_findings(self, db, connection, scan_id, scan_id_2):
        repo = CloudFindingRepository(db)
        findings = [
            CloudFindingData(
                provider="aws", service="ec2", category="security",
                severity="high", title="Active finding", description="",
                resource_id="sg-001", region="us-east-1", rule_id="RULE-001",
            ),
            CloudFindingData(
                provider="aws", service="ec2", category="security",
                severity="medium", title="Stale finding", description="",
                resource_id="sg-002", region="us-east-1", rule_id="RULE-002",
            ),
        ]
        await repo.bulk_upsert(
            findings=findings, connection_id=connection.id,
            provider=connection.provider, scan_id=scan_id,
        )

        # Scan 2: only first finding persists
        current_findings = [findings[0]]
        await repo.bulk_upsert(
            findings=current_findings, connection_id=connection.id,
            provider=connection.provider, scan_id=scan_id_2,
        )
        stale_count = await repo.mark_stale(connection.id, scan_id_2)
        assert stale_count == 1

        # Verify: active finding -> open, stale -> resolved
        result = await db.execute(
            select(CloudFinding).where(CloudFinding.connection_id == connection.id)
        )
        statuses = {r.rule_id: r.status for r in result.scalars().all()}
        assert statuses["RULE-001"] == "open"
        assert statuses["RULE-002"] == "resolved"

    async def test_dashboard_filters_resolved_findings(self, db, connection, scan_id, scan_id_2):
        repo = CloudFindingRepository(db)
        findings = [
            CloudFindingData(
                provider="aws", service="s3", category="security",
                severity="critical", title="Public bucket", description="",
                resource_id="bucket1", region="us-east-1", rule_id="S3-PUBLIC",
            ),
        ]
        await repo.bulk_upsert(
            findings=findings, connection_id=connection.id,
            provider=connection.provider, scan_id=scan_id,
        )

        # Resolve it
        await repo.bulk_upsert(
            findings=[], connection_id=connection.id,
            provider=connection.provider, scan_id=scan_id_2,
        )
        await repo.mark_stale(connection.id, scan_id_2)

        # Dashboard query should only show open/in_progress
        result = await db.execute(
            select(sa_func.count(CloudFinding.id)).where(
                CloudFinding.connection_id == connection.id,
                CloudFinding.status.in_(["open", "in_progress"]),
            )
        )
        assert result.scalar() == 0


# ---------------------------------------------------------------------------
# Cost recommendation lifecycle tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.requires_db
class TestCostLifecycle:
    """Test cost recommendation UPSERT and stale -> resolved."""

    async def test_upsert_costs(self, db, connection, scan_id):
        repo = CloudCostRepository(db)
        costs = [
            CloudCostData(
                provider="aws", service="ec2", title="Reserved instance",
                description="Save by using reserved", resource_id="i-123",
                region="us-east-1", monthly_savings=50.0, current_cost=100.0,
                priority="high", category="compute",
                recommendation_type="reserved_instance",
            ),
        ]
        inserted = await repo.bulk_upsert(
            costs=costs, connection_id=connection.id,
            provider=connection.provider, scan_id=scan_id,
        )
        assert inserted == 1

    async def test_mark_stale_costs(self, db, connection, scan_id, scan_id_2):
        repo = CloudCostRepository(db)
        costs = [
            CloudCostData(
                provider="aws", service="ec2", title="Reserved instance",
                description="", resource_id="i-123", region="us-east-1",
                monthly_savings=50.0, current_cost=100.0, priority="high",
                category="compute", recommendation_type="reserved_instance",
            ),
        ]
        await repo.bulk_upsert(
            costs=costs, connection_id=connection.id,
            provider=connection.provider, scan_id=scan_id,
        )

        # Scan 2: no cost recommendations
        stale = await repo.mark_stale(connection.id, scan_id_2)
        assert stale == 1

        result = await db.execute(
            select(CloudCostRecommendation).where(
                CloudCostRecommendation.connection_id == connection.id,
            )
        )
        row = result.scalar_one()
        assert row.status == "resolved"


# ---------------------------------------------------------------------------
# Compliance lifecycle tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.requires_db
class TestComplianceLifecycle:
    """Test compliance UPSERT and stale -> deleted."""

    async def test_upsert_compliance(self, db, connection, scan_id):
        repo = CloudComplianceRepository(db)
        compliance = [
            {
                "framework": "CIS AWS Foundations",
                "total_controls": 10,
                "passed": 8,
                "failed": 2,
                "warnings": 0,
                "not_applicable": 0,
                "score": 80.0,
                "details": {},
            },
        ]
        inserted = await repo.bulk_upsert(
            compliance=compliance, connection_id=connection.id,
            provider=connection.provider, scan_id=scan_id,
        )
        assert inserted > 0

    async def test_mark_stale_compliance(self, db, connection, scan_id, scan_id_2):
        repo = CloudComplianceRepository(db)
        compliance = [
            {
                "framework": "CIS AWS Foundations",
                "total_controls": 10, "passed": 8, "failed": 2,
                "warnings": 0, "not_applicable": 0, "score": 80.0, "details": {},
            },
        ]
        await repo.bulk_upsert(
            compliance=compliance, connection_id=connection.id,
            provider=connection.provider, scan_id=scan_id,
        )

        stale = await repo.mark_stale(connection.id, scan_id_2)
        assert stale == 1

        result = await db.execute(
            select(CloudComplianceResult).where(
                CloudComplianceResult.connection_id == connection.id,
                CloudComplianceResult.status == "active",
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_dashboard_shows_only_active(self, db, connection, scan_id):
        repo = CloudComplianceRepository(db)
        active = [
            {
                "framework": "CIS AWS Foundations",
                "total_controls": 10, "passed": 8, "failed": 2,
                "warnings": 0, "not_applicable": 0, "score": 80.0, "details": {},
            },
        ]
        await repo.bulk_upsert(
            compliance=active, connection_id=connection.id,
            provider=connection.provider, scan_id=scan_id,
        )

        result = await db.execute(
            select(CloudComplianceResult).where(
                CloudComplianceResult.connection_id == connection.id,
                CloudComplianceResult.status == "active",
            )
        )
        assert len(result.scalars().all()) == 1


# ---------------------------------------------------------------------------
# AI Recommendation lifecycle tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.requires_db
class TestAIRecommendationLifecycle:
    """Test AI recommendation bulk insert, resolve, dashboard count, and API access."""

    @staticmethod
    def _make_recs(connection_id, scan_id, count: int = 2) -> list[dict]:
        return [
            {
                "provider": "aws",
                "service": "ec2",
                "resource_id": f"i-{i}",
                "resource_name": f"server-{i}",
                "category": "security",
                "severity": "high" if i == 0 else "medium",
                "title": f"Test recommendation {i}",
                "summary": f"Summary for recommendation {i}",
                "technical_explanation": f"Technical details for {i}",
                "business_impact": "Could impact operations",
                "estimated_monthly_savings": 50.0 if i == 0 else 0.0,
                "estimated_risk_reduction": 30.0 if i == 0 else 10.0,
                "aws_cli_fix": "aws ec2 modify-instance ...",
                "terraform_fix": None,
                "cloudformation_fix": None,
                "console_steps": ["Step 1", "Step 2"],
                "official_documentation_url": "https://docs.aws.amazon.com/ec2/latest/...",
                "recommendation_source": "engineered",
            }
            for i in range(count)
        ]

    async def test_bulk_insert_recommendations(self, db, connection, scan_id):
        repo = AIRecommendationRepository(db)
        recs = self._make_recs(connection.id, scan_id, count=3)
        inserted = await repo.bulk_insert(
            recommendations=recs,
            connection_id=connection.id,
            scan_id=None,
        )
        assert inserted == 3

        result = await db.execute(
            select(AIRecommendation).where(
                AIRecommendation.connection_id == connection.id,
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 3
        assert rows[0].status == "open"
        assert rows[0].provider == "aws"

    async def test_bulk_insert_empty_list(self, db, connection, scan_id):
        repo = AIRecommendationRepository(db)
        inserted = await repo.bulk_insert(
            recommendations=[],
            connection_id=connection.id,
            scan_id=None,
        )
        assert inserted == 0

    async def test_resolve_previous_open(self, db, connection, scan_id):
        repo = AIRecommendationRepository(db)
        recs = self._make_recs(connection.id, scan_id, count=2)
        await repo.bulk_insert(
            recommendations=recs,
            connection_id=connection.id,
            scan_id=None,
        )

        resolved = await repo.resolve_previous_open(connection.id, scan_id=None)
        assert resolved == 2

        result = await db.execute(
            select(AIRecommendation).where(
                AIRecommendation.connection_id == connection.id,
                AIRecommendation.status == "open",
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_dashboard_count_matches_database(self, db, connection, scan_id):
        repo = AIRecommendationRepository(db)
        recs = self._make_recs(connection.id, scan_id, count=5)
        await repo.bulk_insert(
            recommendations=recs,
            connection_id=connection.id,
            scan_id=None,
        )

        # Count all open
        count = await repo.count_by_connection(connection.id)
        assert count == 5

        # Count with status filter
        open_count = await repo.count_by_connection(connection.id, status="open")
        assert open_count == 5

        # Resolve one
        await repo.resolve_previous_open(connection.id, scan_id=None)

        open_count_after = await repo.count_by_connection(connection.id, status="open")
        assert open_count_after == 0

    async def test_dashboard_summary_query(self, db, connection, scan_id):
        repo = AIRecommendationRepository(db)
        recs = self._make_recs(connection.id, scan_id, count=3)
        await repo.bulk_insert(
            recommendations=recs,
            connection_id=connection.id,
            scan_id=None,
        )

        summary = await repo.get_summary(connection.id)
        assert summary["total"] == 3
        assert summary["by_severity"].get("high", 0) == 1
        assert summary["by_severity"].get("medium", 0) == 2
        assert summary["by_category"].get("security", 0) == 3
        assert summary["by_status"].get("open", 0) == 3
        assert summary["total_monthly_savings"] > 0
        assert summary["avg_risk_reduction"] > 0
        assert summary["critical_count"] == 0

    async def test_get_summary_empty(self, db, connection, scan_id):
        repo = AIRecommendationRepository(db)
        summary = await repo.get_summary(connection.id)
        assert summary["total"] == 0
        assert summary["by_severity"] == {}
        assert summary["by_category"] == {}
        assert summary["by_status"] == {}
        assert summary["total_monthly_savings"] == 0.0
        assert summary["avg_risk_reduction"] == 0.0
        assert summary["critical_count"] == 0

    async def test_recommendation_has_correct_fields(self, db, connection, scan_id):
        repo = AIRecommendationRepository(db)
        recs = self._make_recs(connection.id, scan_id, count=1)
        await repo.bulk_insert(
            recommendations=recs,
            connection_id=connection.id,
            scan_id=None,
        )

        result = await db.execute(
            select(AIRecommendation).where(
                AIRecommendation.connection_id == connection.id,
            )
        )
        row = result.scalar_one()
        assert row.recommendation_id is not None
        assert row.connection_id == connection.id
        assert row.scan_id is None
        assert row.provider == "aws"
        assert row.service == "ec2"
        assert row.resource_id == "i-0"
        assert row.category == "security"
        assert row.severity == "high"
        assert row.title == "Test recommendation 0"
        assert row.summary == "Summary for recommendation 0"
        assert row.technical_explanation == "Technical details for 0"
        assert row.business_impact == "Could impact operations"
        assert row.estimated_monthly_savings == 50.0
        assert row.estimated_risk_reduction == 30.0
        assert row.aws_cli_fix is not None
        assert row.console_steps is not None
        assert row.official_documentation_url is not None
        assert row.recommendation_source == "engineered"
        assert row.status == "open"
        assert row.created_at is not None
        assert row.updated_at is not None
