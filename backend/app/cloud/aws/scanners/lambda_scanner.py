"""Lambda scanner — functions, layers, VPC config."""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any

from app.cloud.base import BaseCloudScanner, CloudFindingData, CloudResourceData

logger = logging.getLogger(__name__)


class LambdaScanner(BaseCloudScanner):
    service_name = "lambda"

    async def scan(self, session: Any, regions: list[str]) -> list[CloudResourceData]:
        resources: list[CloudResourceData] = []
        for region in regions:
            region_resources = 0
            try:
                lam = session.client("lambda", region_name=region)
                paginator = await asyncio.to_thread(lam.get_paginator, "list_functions")
                fn_count = 0
                for page in paginator.paginate():
                    for fn in page.get("Functions", []):
                        fn_count += 1
                        resources.append(CloudResourceData(
                            provider="aws", service="lambda",
                            resource_id=fn["FunctionArn"], resource_name=fn["FunctionName"],
                            resource_type="function", region=region,
                            status="active",
                            configuration={
                                "runtime": fn.get("Runtime"),
                                "handler": fn.get("Handler"),
                                "memory_size": fn.get("MemorySize"),
                                "timeout": fn.get("Timeout"),
                                "role": fn.get("Role"),
                                "vpc_config": fn.get("VpcConfig", {}),
                                "tracing_config": fn.get("TracingConfig", {}),
                                "last_update_status": fn.get("LastUpdateStatus"),
                                "code_size": fn.get("CodeSize"),
                            },
                            tags=fn.get("Tags", {}),
                            created_at=fn.get("LastModified"),
                        ))
                logger.info("Lambda ListFunctions: service=lambda region=%s api=ListFunctions found=%d", region, fn_count)
                region_resources = fn_count
            except Exception:
                tb = traceback.format_exc()
                logger.warning("Lambda scan failed for region %s\n%s", region, tb)
            logger.info("Lambda region_summary: service=lambda region=%s total_resources=%d", region, region_resources)
        return resources

    async def check_security(self, session: Any, resources: list[CloudResourceData]) -> list[CloudFindingData]:
        findings: list[CloudFindingData] = []
        for r in resources:
            if r.resource_type != "function":
                continue
            tracing = r.configuration.get("tracing_config", {}).get("Mode")
            if tracing != "Active":
                findings.append(CloudFindingData(
                    provider="aws", service="lambda", category="security", severity="low",
                    title=f"Lambda function {r.resource_name} does not have X-Ray tracing active",
                    description=f"Function {r.resource_name} in {r.region} does not have active X-Ray tracing.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="lambda-no-tracing", compliance_frameworks=["aws-cis"],
                    remediation="Set TracingConfig.Mode to Active for visibility.",
                ))
            vpc = r.configuration.get("vpc_config", {})
            if not vpc.get("SubnetIds"):
                findings.append(CloudFindingData(
                    provider="aws", service="lambda", category="security", severity="info",
                    title=f"Lambda function {r.resource_name} is not in a VPC",
                    description=f"Function {r.resource_name} in {r.region} does not run inside a VPC.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="lambda-no-vpc",
                    remediation="Configure VPC settings if the function needs to access VPC resources.",
                ))
        return findings
