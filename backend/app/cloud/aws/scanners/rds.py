"""RDS scanner — instances, storage, backups, encryption, public access."""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any

from app.cloud.base import BaseCloudScanner, CloudCostData, CloudFindingData, CloudResourceData

logger = logging.getLogger(__name__)


class RDSScanner(BaseCloudScanner):
    service_name = "rds"

    async def scan(self, session: Any, regions: list[str]) -> list[CloudResourceData]:
        resources: list[CloudResourceData] = []
        for region in regions:
            region_resources = 0
            try:
                rds = session.client("rds", region_name=region)
                paginator = await asyncio.to_thread(rds.get_paginator, "describe_db_instances")
                db_count = 0
                for page in paginator.paginate():
                    for db in page.get("DBInstances", []):
                        db_count += 1
                        resources.append(CloudResourceData(
                            provider="aws", service="rds",
                            resource_id=db["DBInstanceIdentifier"],
                            resource_name=db["DBInstanceIdentifier"],
                            resource_type="db_instance", region=region,
                            status=db.get("DBInstanceStatus", "unknown"),
                            configuration={
                                "engine": db.get("Engine"),
                                "engine_version": db.get("EngineVersion"),
                                "instance_class": db.get("DBInstanceClass"),
                                "allocated_storage": db.get("AllocatedStorage"),
                                "storage_encrypted": db.get("StorageEncrypted", False),
                                "multi_az": db.get("MultiAZ", False),
                                "publicly_accessible": db.get("PubliclyAccessible", False),
                                "auto_minor_version_upgrade": db.get("AutoMinorVersionUpgrade", False),
                                "backup_retention_period": db.get("BackupRetentionPeriod", 0),
                                "vpc_id": db.get("DBSubnetGroup", {}).get("VpcId"),
                            },
                            tags={t["Key"]: t["Value"] for t in db.get("TagList", [])},
                            created_at=db.get("InstanceCreateTime"),
                        ))
                logger.info("RDS DescribeDBInstances: service=rds region=%s api=DescribeDBInstances found=%d", region, db_count)
                region_resources = db_count
            except Exception:
                tb = traceback.format_exc()
                logger.warning("RDS scan failed for region %s\n%s", region, tb)
            logger.info("RDS region_summary: service=rds region=%s total_resources=%d", region, region_resources)
        return resources

    async def check_security(self, session: Any, resources: list[CloudResourceData]) -> list[CloudFindingData]:
        findings: list[CloudFindingData] = []
        for r in resources:
            if r.resource_type != "db_instance":
                continue
            if r.configuration.get("publicly_accessible"):
                findings.append(CloudFindingData(
                    provider="aws", service="rds", category="security", severity="critical",
                    title=f"RDS instance {r.resource_id} is publicly accessible",
                    description=f"RDS instance {r.resource_id} in {r.region} is publicly accessible from the internet.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="rds-public-access", compliance_frameworks=["aws-cis", "pci-dss"],
                    remediation="Set PubliclyAccessible to false.",
                ))
            if not r.configuration.get("storage_encrypted"):
                findings.append(CloudFindingData(
                    provider="aws", service="rds", category="security", severity="high",
                    title=f"RDS instance {r.resource_id} storage is not encrypted",
                    description=f"RDS instance {r.resource_id} does not have storage encryption enabled.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="rds-unencrypted", compliance_frameworks=["aws-cis", "pci-dss"],
                    remediation="Enable storage encryption for the RDS instance.",
                ))
            if r.configuration.get("backup_retention_period", 0) == 0:
                findings.append(CloudFindingData(
                    provider="aws", service="rds", category="compliance", severity="medium",
                    title=f"RDS instance {r.resource_id} has no automated backups",
                    description=f"RDS instance {r.resource_id} has backup retention set to 0 days.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="rds-no-backups", compliance_frameworks=["aws-cis"],
                    remediation="Set BackupRetentionPeriod to a positive value (recommended: 7 days).",
                ))
            if not r.configuration.get("auto_minor_version_upgrade"):
                findings.append(CloudFindingData(
                    provider="aws", service="rds", category="compliance", severity="low",
                    title=f"RDS instance {r.resource_id} auto minor version upgrade is disabled",
                    description=f"RDS instance {r.resource_id} does not auto-apply minor version upgrades.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="rds-no-auto-upgrade",
                    remediation="Enable AutoMinorVersionUpgrade.",
                ))
        return findings

    async def check_cost(self, session: Any, resources: list[CloudResourceData]) -> list[CloudCostData]:
        cost_recs: list[CloudCostData] = []
        for r in resources:
            if r.resource_type == "db_instance" and not r.configuration.get("multi_az"):
                cost_recs.append(CloudCostData(
                    provider="aws", service="rds",
                    title=f"RDS instance {r.resource_id} is single-AZ",
                    description=f"Instance {r.resource_id} ({r.configuration.get('instance_class')}) runs in a single AZ.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    monthly_savings=0.0, current_cost=0.0,
                    priority="info", category="availability",
                    recommendation_type="review",
                    estimated_impact="Consider Multi-AZ for production workloads.",
                ))
        return cost_recs
