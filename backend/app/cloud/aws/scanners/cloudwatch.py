"""CloudWatch scanner — log groups, alarms, dashboards."""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any

from app.cloud.base import BaseCloudScanner, CloudFindingData, CloudResourceData

logger = logging.getLogger(__name__)


class CloudWatchScanner(BaseCloudScanner):
    service_name = "cloudwatch"

    async def scan(self, session: Any, regions: list[str]) -> list[CloudResourceData]:
        resources: list[CloudResourceData] = []
        for region in regions:
            region_resources = 0
            try:
                cw = session.client("cloudwatch", region_name=region)
                logs = session.client("logs", region_name=region)

                # DescribeLogGroups
                lg_paginator = await asyncio.to_thread(logs.get_paginator, "describe_log_groups")
                lg_count = 0
                for page in lg_paginator.paginate():
                    for lg in page.get("logGroups", []):
                        lg_count += 1
                        resources.append(CloudResourceData(
                            provider="aws", service="cloudwatch",
                            resource_id=lg.get("arn", lg["logGroupName"]),
                            resource_name=lg["logGroupName"],
                            resource_type="log_group", region=region, status="active",
                            configuration={
                                "retention_days": lg.get("retentionInDays"),
                                "stored_bytes": lg.get("storedBytes", 0),
                                "kms_key_id": lg.get("kmsKeyId"),
                            },
                            created_at=lg.get("creationTime"),
                        ))
                logger.info("CloudWatch DescribeLogGroups: service=cloudwatch region=%s api=DescribeLogGroups found=%d", region, lg_count)

                # DescribeAlarms
                alarm_paginator = await asyncio.to_thread(cw.get_paginator, "describe_alarms")
                alarm_count = 0
                for page in alarm_paginator.paginate():
                    for alarm in page.get("MetricAlarms", []):
                        alarm_count += 1
                        resources.append(CloudResourceData(
                            provider="aws", service="cloudwatch",
                            resource_id=alarm["AlarmArn"], resource_name=alarm["AlarmName"],
                            resource_type="alarm", region=region,
                            status=alarm.get("StateValue", "UNKNOWN"),
                            configuration={
                                "namespace": alarm.get("Namespace"),
                                "metric_name": alarm.get("MetricName"),
                                "comparison_operator": alarm.get("ComparisonOperator"),
                                "threshold": alarm.get("Threshold"),
                            },
                            created_at=alarm.get("AlarmConfigurationUpdatedTimestamp"),
                        ))
                logger.info("CloudWatch DescribeAlarms: service=cloudwatch region=%s api=DescribeAlarms found=%d", region, alarm_count)

                region_resources = lg_count + alarm_count
            except Exception:
                tb = traceback.format_exc()
                logger.warning("CloudWatch scan failed for region %s\n%s", region, tb)
            logger.info("CloudWatch region_summary: service=cloudwatch region=%s total_resources=%d", region, region_resources)
        return resources

    async def check_security(self, session: Any, resources: list[CloudResourceData]) -> list[CloudFindingData]:
        findings: list[CloudFindingData] = []
        for r in resources:
            if r.resource_type == "log_group" and not r.configuration.get("retention_days"):
                findings.append(CloudFindingData(
                    provider="aws", service="cloudwatch", category="compliance", severity="low",
                    title=f"Log group {r.resource_name} has no retention policy",
                    description=f"Log group {r.resource_name} in {r.region} retains logs forever.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="cw-no-retention", compliance_frameworks=["aws-cis"],
                    remediation="Set a retention policy to control log storage and costs.",
                ))
            elif r.resource_type == "alarm":
                if r.status == "INSUFFICIENT_DATA":
                    findings.append(CloudFindingData(
                        provider="aws", service="cloudwatch", category="compliance", severity="info",
                        title=f"Alarm {r.resource_name} has insufficient data",
                        description=f"CloudWatch alarm {r.resource_name} in {r.region} has insufficient data.",
                        resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                        rule_id="cw-alarm-insufficient-data",
                        remediation="Verify the alarm configuration and metric data source.",
                    ))
        return findings
