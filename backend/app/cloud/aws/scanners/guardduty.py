"""GuardDuty scanner — detector status, findings."""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any

from app.cloud.base import BaseCloudScanner, CloudFindingData, CloudResourceData

logger = logging.getLogger(__name__)


class GuardDutyScanner(BaseCloudScanner):
    service_name = "guardduty"

    async def scan(self, session: Any, regions: list[str]) -> list[CloudResourceData]:
        resources: list[CloudResourceData] = []
        for region in regions:
            region_resources = 0
            try:
                gd = session.client("guardduty", region_name=region)
                detectors_resp = await asyncio.to_thread(gd.list_detectors)
                detector_ids = detectors_resp.get("DetectorIds", [])
                logger.info("GuardDuty ListDetectors: service=guardduty region=%s api=ListDetectors found=%d", region, len(detector_ids))
                for det_id in detector_ids:
                    desc = await asyncio.to_thread(gd.describe_detector, DetectorId=det_id)
                    detector = desc.get("Detector", {})
                    region_resources += 1
                    resources.append(CloudResourceData(
                        provider="aws", service="guardduty",
                        resource_id=det_id, resource_name=det_id,
                        resource_type="detector", region=region,
                        status="active" if detector.get("Status") == "ENABLED" else "disabled",
                        configuration={
                            "status": detector.get("Status"),
                            "finding_publishing_frequency": detector.get("FindingPublishingFrequency"),
                            "service_role": detector.get("ServiceRole"),
                        },
                        created_at=detector.get("CreatedAt"),
                    ))

            except Exception:
                tb = traceback.format_exc()
                logger.warning("GuardDuty scan failed for region %s\n%s", region, tb)
            logger.info("GuardDuty region_summary: service=guardduty region=%s total_resources=%d", region, region_resources)
        return resources

    async def check_security(self, session: Any, resources: list[CloudResourceData]) -> list[CloudFindingData]:
        findings: list[CloudFindingData] = []
        for r in resources:
            if r.resource_type == "detector" and r.status != "active":
                findings.append(CloudFindingData(
                    provider="aws", service="guardduty", category="security", severity="high",
                    title=f"GuardDuty is not enabled in {r.region}",
                    description=f"GuardDuty detector {r.resource_id} in {r.region} is not enabled.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="guardduty-not-enabled", compliance_frameworks=["aws-cis"],
                    remediation="Enable GuardDuty in the region.",
                ))
            elif r.resource_type == "detector" and r.status == "active":
                freq = r.configuration.get("finding_publishing_frequency")
                if freq and freq not in ("FIFTEEN_MINUTES", "ONE_HOUR"):
                    findings.append(CloudFindingData(
                        provider="aws", service="guardduty", category="security", severity="low",
                        title=f"GuardDuty {r.resource_id} finding frequency is {freq}",
                        description=f"GuardDuty detector publishes findings every {freq}.",
                        resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                        rule_id="guardduty-low-frequency",
                        remediation="Set FindingPublishingFrequency to FIFTEEN_MINUTES or ONE_HOUR.",
                    ))
        return findings
