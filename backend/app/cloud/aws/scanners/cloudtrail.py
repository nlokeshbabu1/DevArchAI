"""CloudTrail scanner — trails, logging status, multi-region."""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any

from app.cloud.base import BaseCloudScanner, CloudFindingData, CloudResourceData

logger = logging.getLogger(__name__)


class CloudTrailScanner(BaseCloudScanner):
    service_name = "cloudtrail"

    async def scan(self, session: Any, regions: list[str]) -> list[CloudResourceData]:
        resources: list[CloudResourceData] = []
        try:
            ct = session.client("cloudtrail")
            trails_resp = await asyncio.to_thread(ct.describe_trails)
            trail_list = trails_resp.get("trailList", [])
            logger.info("CloudTrail DescribeTrails: service=cloudtrail api=DescribeTrails found=%d", len(trail_list))
            for trail in trail_list:
                name = trail.get("Name", "")
                status = {}
                try:
                    st = await asyncio.to_thread(ct.get_trail_status, Name=name)
                    status = st
                except Exception:
                    pass
                resources.append(CloudResourceData(
                    provider="aws", service="cloudtrail",
                    resource_id=trail.get("TrailARN", name), resource_name=name,
                    resource_type="trail", region=trail.get("HomeRegion", ""),
                    status="logging" if status.get("IsLogging") else "stopped",
                    configuration={
                        "s3_bucket": trail.get("S3BucketName"),
                        "is_multi_region": trail.get("IsMultiRegionTrail", False),
                        "is_global": trail.get("IsOrganizationTrail", False),
                        "log_file_validation": trail.get("LogFileValidationEnabled", False),
                        "cloudwatch_logs_group": trail.get("CloudWatchLogsLogGroupArn"),
                        "kms_key_id": trail.get("KmsKeyId"),
                    },
                ))
            logger.info("CloudTrail scan_complete: service=cloudtrail total_trails=%d", len(resources))
        except Exception:
            tb = traceback.format_exc()
            logger.warning("CloudTrail scan failed\n%s", tb)
        return resources

    async def check_security(self, session: Any, resources: list[CloudResourceData]) -> list[CloudFindingData]:
        findings: list[CloudFindingData] = []
        for r in resources:
            if r.resource_type != "trail":
                continue
            if not r.configuration.get("is_multi_region"):
                findings.append(CloudFindingData(
                    provider="aws", service="cloudtrail", category="security", severity="medium",
                    title=f"CloudTrail {r.resource_name} is not multi-region",
                    description=f"Trail {r.resource_name} does not cover all regions.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="cloudtrail-no-multi-region", compliance_frameworks=["aws-cis"],
                    remediation="Enable IsMultiRegionTrail on the trail.",
                ))
            if not r.configuration.get("log_file_validation"):
                findings.append(CloudFindingData(
                    provider="aws", service="cloudtrail", category="security", severity="medium",
                    title=f"CloudTrail {r.resource_name} does not have log file validation",
                    description=f"Trail {r.resource_name} does not have log file integrity validation enabled.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="cloudtrail-no-validation", compliance_frameworks=["aws-cis"],
                    remediation="Enable LogFileValidationEnabled on the trail.",
                ))
            if not r.configuration.get("kms_key_id"):
                findings.append(CloudFindingData(
                    provider="aws", service="cloudtrail", category="security", severity="low",
                    title=f"CloudTrail {r.resource_name} logs are not encrypted with KMS",
                    description=f"Trail {r.resource_name} does not use a KMS key for log encryption.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="cloudtrail-no-kms", compliance_frameworks=["aws-cis"],
                    remediation="Configure a KmsKeyId for the trail.",
                ))
            if r.status != "logging":
                findings.append(CloudFindingData(
                    provider="aws", service="cloudtrail", category="compliance", severity="high",
                    title=f"CloudTrail {r.resource_name} is not logging",
                    description=f"Trail {r.resource_name} is not currently logging.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="cloudtrail-not-logging", compliance_frameworks=["aws-cis"],
                    remediation="Start logging on the trail.",
                ))
        return findings
