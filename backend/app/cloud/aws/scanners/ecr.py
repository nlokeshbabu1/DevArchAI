"""ECR scanner — repositories, image scanning."""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any

from app.cloud.base import BaseCloudScanner, CloudFindingData, CloudResourceData

logger = logging.getLogger(__name__)


class ECRScanner(BaseCloudScanner):
    service_name = "ecr"

    async def scan(self, session: Any, regions: list[str]) -> list[CloudResourceData]:
        resources: list[CloudResourceData] = []
        for region in regions:
            region_resources = 0
            try:
                ecr = session.client("ecr", region_name=region)
                paginator = await asyncio.to_thread(ecr.get_paginator, "describe_repositories")
                total_repos = 0
                for page in paginator.paginate():
                    repos = page.get("repositories", [])
                    total_repos += len(repos)
                    for repo in repos:
                        region_resources += 1
                        resources.append(CloudResourceData(
                            provider="aws", service="ecr",
                            resource_id=repo["repositoryArn"],
                            resource_name=repo["repositoryName"],
                            resource_type="repository", region=region, status="active",
                            configuration={
                                "uri": repo.get("repositoryUri"),
                                "image_tag_mutability": repo.get("imageTagMutability"),
                                "scan_on_push": repo.get("imageScanningConfiguration", {}).get("scanOnPush", False),
                                "encryption_configuration": repo.get("encryptionConfiguration", {}),
                            },
                            tags={t["Key"]: t["Value"] for t in repo.get("tags", [])},
                            created_at=repo.get("createdAt"),
                        ))
                logger.info("ECR DescribeRepositories: service=ecr region=%s api=DescribeRepositories found=%d", region, total_repos)
            except Exception:
                tb = traceback.format_exc()
                logger.warning("ECR scan failed for region %s\n%s", region, tb)
            logger.info("ECR region_summary: service=ecr region=%s total_resources=%d", region, region_resources)
        return resources

    async def check_security(self, session: Any, resources: list[CloudResourceData]) -> list[CloudFindingData]:
        findings: list[CloudFindingData] = []
        for r in resources:
            if r.resource_type != "repository":
                continue
            if not r.configuration.get("scan_on_push"):
                findings.append(CloudFindingData(
                    provider="aws", service="ecr", category="security", severity="medium",
                    title=f"ECR repository {r.resource_name} does not scan images on push",
                    description=f"Repository {r.resource_name} in {r.region} does not have scanOnPush enabled.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="ecr-no-scan-on-push", compliance_frameworks=["aws-cis"],
                    remediation="Enable imageScanningConfiguration.scanOnPush on the repository.",
                ))
            if r.configuration.get("image_tag_mutability") != "IMMUTABLE":
                findings.append(CloudFindingData(
                    provider="aws", service="ecr", category="security", severity="low",
                    title=f"ECR repository {r.resource_name} allows mutable image tags",
                    description=f"Repository {r.resource_name} in {r.region} has mutable image tags.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="ecr-mutable-tags", compliance_frameworks=["aws-cis"],
                    remediation="Set imageTagMutability to IMMUTABLE.",
                ))
        return findings
