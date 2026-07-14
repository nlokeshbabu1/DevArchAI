"""AWS background scan orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import delete, select

from app.db.session import get_session_factory
from app.models.aws import AWSAccount, AWSCostRecommendation, AWSFinding, AWSInventory
from app.services.aws.aws_client import build_session, decrypt_account_credentials
from app.services.aws.aws_cost_service import AWSCostService
from app.services.aws.aws_iam_service import AWSIAMService
from app.services.aws.aws_inventory_service import AWSInventoryService
from app.services.aws.aws_security_service import AWSSecurityService

logger = structlog.get_logger(__name__)


class AWSScanService:
    """Run long AWS scans outside request handling."""

    def __init__(self) -> None:
        self.inventory_service = AWSInventoryService()
        self.security_service = AWSSecurityService()
        self.cost_service = AWSCostService()
        self.iam_service = AWSIAMService()

    async def run_full_scan(self, account_id: UUID) -> None:
        session_factory = get_session_factory()
        async with session_factory() as db:
            account = await db.scalar(select(AWSAccount).where(AWSAccount.id == account_id))
            if not account:
                return

            account.scan_status = "running"
            account.scan_progress = 5
            account.last_error = None
            await db.commit()
            logger.info("AWS inventory scan started", aws_account_id=str(account.id), cloud_account_id=account.account_id)

            try:
                credentials = decrypt_account_credentials(account)
                aws_session = build_session(credentials)

                inventory = await self.inventory_service.collect(aws_session, account.default_region)
                await db.execute(delete(AWSInventory).where(AWSInventory.account_id == account.id))
                db.add_all([
                    AWSInventory(
                        account_id=account.id,
                        resource_type=item["resource_type"],
                        resource_id=item["resource_id"],
                        name=item.get("name"),
                        region=item.get("region"),
                        metadata_json=item.get("metadata", {}),
                    )
                    for item in inventory
                ])
                account.scan_progress = 35
                await db.commit()

                security_findings = await self.security_service.analyze(aws_session, account.default_region)
                iam_findings = await self.iam_service.analyze(aws_session, account.default_region)
                await db.execute(delete(AWSFinding).where(AWSFinding.account_id == account.id))
                db.add_all([
                    AWSFinding(
                        account_id=account.id,
                        category=item["category"],
                        severity=item["severity"],
                        title=item["title"],
                        description=item["description"],
                        resource_type=item.get("resource_type"),
                        resource_id=item.get("resource_id"),
                        region=item.get("region"),
                        recommendation=item.get("recommendation"),
                        metadata_json=item.get("metadata", {}),
                    )
                    for item in [*security_findings, *iam_findings]
                ])
                account.scan_progress = 70
                await db.commit()

                cost_recommendations = await self.cost_service.analyze(aws_session, account.default_region)
                await db.execute(delete(AWSCostRecommendation).where(AWSCostRecommendation.account_id == account.id))
                db.add_all([
                    AWSCostRecommendation(
                        account_id=account.id,
                        recommendation_type=item["recommendation_type"],
                        title=item["title"],
                        description=item["description"],
                        resource_type=item.get("resource_type"),
                        resource_id=item.get("resource_id"),
                        region=item.get("region"),
                        estimated_monthly_savings=item.get("estimated_monthly_savings", 0.0),
                        metadata_json=item.get("metadata", {}),
                    )
                    for item in cost_recommendations
                ])
                account.scan_status = "completed"
                account.scan_progress = 100
                account.last_scanned_at = datetime.now(UTC)
                await db.commit()
                logger.info("AWS cost analysis completed", aws_account_id=str(account.id), recommendations=len(cost_recommendations))
            except Exception as exc:
                account.scan_status = "failed"
                account.last_error = "AWS scan failed. Check IAM permissions and retry."
                await db.commit()
                logger.error("AWS API failure", aws_account_id=str(account.id), error=str(exc), exc_info=True)
