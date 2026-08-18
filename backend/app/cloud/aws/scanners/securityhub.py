"""Security Hub scanner — hub status, findings count."""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any

from app.cloud.base import BaseCloudScanner, CloudFindingData, CloudResourceData

logger = logging.getLogger(__name__)


class SecurityHubScanner(BaseCloudScanner):
    service_name = "securityhub"

    async def scan(self, session: Any, regions: list[str]) -> list[CloudResourceData]:
        resources: list[CloudResourceData] = []
        for region in regions:
            region_resources = 0
            try:
                sh = session.client("securityhub", region_name=region)
                hub = await asyncio.to_thread(sh.describe_hub)
                if hub:
                    region_resources += 1
                    resources.append(CloudResourceData(
                        provider="aws", service="securityhub",
                        resource_id=hub.get("HubArn", ""),
                        resource_name="SecurityHub",
                        resource_type="hub", region=region, status="active",
                        configuration={
                            "subscribed_at": str(hub.get("SubscribedAt", "")),
                            "auto_enable_controls": hub.get("AutoEnableControls", True),
                            "controls_status": hub.get("ControlsProviderName"),
                        },
                    ))
                    logger.info("SecurityHub DescribeHub: service=securityhub region=%s api=DescribeHub found=1", region)
            except Exception as exc:
                if "InvalidAccessException" in str(exc) or "Account" in str(exc):
                    region_resources += 1
                    resources.append(CloudResourceData(
                        provider="aws", service="securityhub",
                        resource_id=f"securityhub-{region}",
                        resource_name="SecurityHub (not enabled)",
                        resource_type="hub", region=region, status="not_enabled",
                        configuration={},
                    ))
                    logger.info("SecurityHub DescribeHub: service=securityhub region=%s status=not_enabled", region)
                else:
                    tb = traceback.format_exc()
                    logger.warning("SecurityHub scan failed for region %s\n%s", region, tb)
            logger.info("SecurityHub region_summary: service=securityhub region=%s total_resources=%d", region, region_resources)
        return resources

    async def check_security(self, session: Any, resources: list[CloudResourceData]) -> list[CloudFindingData]:
        findings: list[CloudFindingData] = []
        for r in resources:
            if r.resource_type == "hub" and r.status == "not_enabled":
                findings.append(CloudFindingData(
                    provider="aws", service="securityhub", category="security", severity="high",
                    title=f"Security Hub is not enabled in {r.region}",
                    description=f"AWS Security Hub is not enabled in region {r.region}.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="securityhub-not-enabled",
                    compliance_frameworks=["aws-cis"],
                    remediation="Enable Security Hub in the region.",
                ))
        return findings
