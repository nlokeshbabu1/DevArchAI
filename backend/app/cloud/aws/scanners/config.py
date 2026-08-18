"""AWS Config scanner — recorder status, rule compliance."""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any

from app.cloud.base import BaseCloudScanner, CloudFindingData, CloudResourceData

logger = logging.getLogger(__name__)


class ConfigScanner(BaseCloudScanner):
    service_name = "config"

    async def scan(self, session: Any, regions: list[str]) -> list[CloudResourceData]:
        resources: list[CloudResourceData] = []
        for region in regions:
            region_resources = 0
            try:
                cfg = session.client("config", region_name=region)
                # Recorders
                rec_resp = await asyncio.to_thread(cfg.describe_configuration_recorders)
                recorders = rec_resp.get("ConfigurationRecorders", [])
                logger.info("Config DescribeConfigurationRecorders: service=config region=%s api=DescribeConfigurationRecorders found=%d", region, len(recorders))
                for rec in recorders:
                    name = rec.get("name", "")
                    status_resp = await asyncio.to_thread(
                        cfg.describe_configuration_recorder_status, ConfigurationRecorderNames=[name]
                    )
                    recorder_status = status_resp.get("ConfigurationRecordersStatus", [{}])
                    is_running = any(s.get("recording") for s in recorder_status)
                    region_resources += 1
                    resources.append(CloudResourceData(
                        provider="aws", service="config",
                        resource_id=name, resource_name=name,
                        resource_type="recorder", region=region,
                        status="recording" if is_running else "stopped",
                        configuration={
                            "all_supported": rec.get("recordingGroup", {}).get("allSupported", False),
                            "resource_types": rec.get("recordingGroup", {}).get("resourceTypes", []),
                            "include_global_resources": rec.get("recordingGroup", {}).get("includeGlobalResourceTypes", False),
                        },
                    ))
                # Delivery channels
                dc_resp = await asyncio.to_thread(cfg.describe_delivery_channels)
                channels = dc_resp.get("DeliveryChannels", [])
                logger.info("Config DescribeDeliveryChannels: service=config region=%s api=DescribeDeliveryChannels found=%d", region, len(channels))
                for dc in channels:
                    region_resources += 1
                    resources.append(CloudResourceData(
                        provider="aws", service="config",
                        resource_id=dc.get("name", ""),
                        resource_name=dc.get("name", ""),
                        resource_type="delivery_channel", region=region, status="active",
                        configuration={
                            "s3_bucket": dc.get("s3BucketName"),
                            "sns_topic": dc.get("snsTopicARN"),
                            "frequency": dc.get("config_snapshotDeliveryProperties", {}).get(
                                "deliveryFrequency"
                            ),
                        },
                    ))
                # Compliance rules
                rules_paginator = await asyncio.to_thread(cfg.get_paginator, "describe_config_rules")
                total_rules = 0
                for page in rules_paginator.paginate():
                    rules = page.get("ConfigRules", [])
                    total_rules += len(rules)
                    for rule in rules:
                        region_resources += 1
                        resources.append(CloudResourceData(
                            provider="aws", service="config",
                            resource_id=rule.get("ConfigRuleArn", rule["ConfigRuleName"]),
                            resource_name=rule["ConfigRuleName"],
                            resource_type="rule", region=region, status="active",
                            configuration={
                                "source": rule.get("source", {}),
                                "maximum_execution_frequency": rule.get("MaximumExecutionFrequency"),
                            },
                        ))
                logger.info("Config DescribeConfigRules: service=config region=%s api=DescribeConfigRules found=%d", region, total_rules)
            except Exception:
                tb = traceback.format_exc()
                logger.warning("Config scan failed for region %s\n%s", region, tb)
            logger.info("Config region_summary: service=config region=%s total_resources=%d", region, region_resources)
        return resources

    async def check_security(self, session: Any, resources: list[CloudResourceData]) -> list[CloudFindingData]:
        findings: list[CloudFindingData] = []
        for r in resources:
            if r.resource_type == "recorder":
                if r.status != "recording":
                    findings.append(CloudFindingData(
                        provider="aws", service="config", category="compliance", severity="high",
                        title=f"AWS Config recorder {r.resource_name} is not recording",
                        description=f"Config recorder {r.resource_name} in {r.region} is not recording.",
                        resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                        rule_id="config-recorder-off", compliance_frameworks=["aws-cis"],
                        remediation="Start the configuration recorder.",
                    ))
                if not r.configuration.get("include_global_resources"):
                    findings.append(CloudFindingData(
                        provider="aws", service="config", category="compliance", severity="medium",
                        title=f"Config recorder {r.resource_name} does not track global resources",
                        description=f"Config recorder {r.resource_name} does not include global resource types.",
                        resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                        rule_id="config-no-global", compliance_frameworks=["aws-cis"],
                        remediation="Enable includeGlobalResourceTypes in the recording group.",
                    ))
            elif r.resource_type == "delivery_channel":
                if not r.configuration.get("sns_topic"):
                    findings.append(CloudFindingData(
                        provider="aws", service="config", category="compliance", severity="low",
                        title=f"Config delivery channel {r.resource_name} has no SNS topic",
                        description=f"Delivery channel {r.resource_name} in {r.region} does not have an SNS topic configured.",
                        resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                        rule_id="config-no-sns",
                        remediation="Configure an SNS topic for the delivery channel.",
                    ))
        return findings
