"""KMS scanner — keys, rotation status."""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any

from app.cloud.base import BaseCloudScanner, CloudFindingData, CloudResourceData

logger = logging.getLogger(__name__)


class KMSScanner(BaseCloudScanner):
    service_name = "kms"

    async def scan(self, session: Any, regions: list[str]) -> list[CloudResourceData]:
        resources: list[CloudResourceData] = []
        for region in regions:
            region_resources = 0
            try:
                kms = session.client("kms", region_name=region)
                paginator = await asyncio.to_thread(kms.get_paginator, "list_keys")
                total_keys = 0
                for page in paginator.paginate():
                    keys = page.get("Keys", [])
                    total_keys += len(keys)
                    for key in keys:
                        key_id = key["KeyId"]
                        desc = await asyncio.to_thread(kms.describe_key, KeyId=key_id)
                        metadata = desc.get("KeyMetadata", {})
                        rotation = {}
                        try:
                            rotation = await asyncio.to_thread(
                                kms.get_key_rotation_status, KeyId=key_id
                            )
                        except Exception:
                            pass
                        region_resources += 1
                        resources.append(CloudResourceData(
                            provider="aws", service="kms",
                            resource_id=key_id,
                            resource_name=metadata.get("Alias", key_id),
                            resource_type="key", region=region,
                            status=metadata.get("KeyState", "unknown"),
                            configuration={
                                "arn": metadata.get("Arn"),
                                "key_usage": metadata.get("KeyUsage"),
                                "key_spec": metadata.get("KeySpec"),
                                "key_origin": metadata.get("Origin"),
                                "automatic_rotation_enabled": rotation.get("KeyRotationEnabled", False),
                                "description": metadata.get("Description", ""),
                            },
                            created_at=metadata.get("CreationDate"),
                        ))
                logger.info("KMS ListKeys: service=kms region=%s api=ListKeys found=%d", region, total_keys)
            except Exception:
                tb = traceback.format_exc()
                logger.warning("KMS scan failed for region %s\n%s", region, tb)
            logger.info("KMS region_summary: service=kms region=%s total_resources=%d", region, region_resources)
        return resources

    async def check_security(self, session: Any, resources: list[CloudResourceData]) -> list[CloudFindingData]:
        findings: list[CloudFindingData] = []
        for r in resources:
            if r.resource_type != "key":
                continue
            if r.status in ("Enabled", "PendingDeletion"):
                if not r.configuration.get("automatic_rotation_enabled"):
                    findings.append(CloudFindingData(
                        provider="aws", service="kms", category="security", severity="medium",
                        title=f"KMS key {r.resource_id} does not have automatic rotation enabled",
                        description=f"KMS key {r.resource_id} in {r.region} does not have automatic key rotation.",
                        resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                        rule_id="kms-no-rotation", compliance_frameworks=["aws-cis", "pci-dss"],
                        remediation="Enable automatic key rotation for the KMS key.",
                    ))
        return findings
