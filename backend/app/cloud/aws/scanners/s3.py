"""S3 scanner — buckets, encryption, public access, versioning, logging."""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any

from app.cloud.base import BaseCloudScanner, CloudFindingData, CloudResourceData

logger = logging.getLogger(__name__)


class S3Scanner(BaseCloudScanner):
    service_name = "s3"

    async def scan(self, session: Any, regions: list[str]) -> list[CloudResourceData]:
        resources: list[CloudResourceData] = []
        try:
            s3 = session.client("s3")
            resp = await asyncio.to_thread(s3.list_buckets)
            buckets = resp.get("Buckets", [])
            logger.info("S3 ListBuckets: service=s3 api=ListBuckets found=%d", len(buckets))
            for bucket in buckets:
                name = bucket["Name"]
                region = "us-east-1"
                try:
                    loc = await asyncio.to_thread(s3.get_bucket_location, Bucket=name)
                    region = loc.get("LocationConstraint") or "us-east-1"
                except Exception:
                    pass
                resources.append(CloudResourceData(
                    provider="aws", service="s3",
                    resource_id=name, resource_name=name,
                    resource_type="bucket", region=region, status="active",
                    configuration={"creation_date": bucket.get("CreationDate")},
                    created_at=bucket.get("CreationDate"),
                ))
            logger.info("S3 scan_complete: service=s3 total_buckets=%d", len(resources))
        except Exception:
            tb = traceback.format_exc()
            logger.warning("S3 scan failed\n%s", tb)
        return resources

    async def check_security(self, session: Any, resources: list[CloudResourceData]) -> list[CloudFindingData]:
        findings: list[CloudFindingData] = []
        try:
            s3 = session.client("s3")
            for r in resources:
                if r.resource_type != "bucket":
                    continue
                name = r.resource_id
                # Public access
                try:
                    pub = await asyncio.to_thread(s3.get_public_access_block, Bucket=name)
                    config = pub.get("PublicAccessBlockConfiguration", {})
                    if not all(config.get(k, False) for k in [
                        "BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets"
                    ]):
                        findings.append(CloudFindingData(
                            provider="aws", service="s3", category="security", severity="high",
                            title=f"Bucket {name} does not block all public access",
                            description=f"Bucket {name} does not have all public access block settings enabled.",
                            resource_id=name, resource_type="bucket", region=r.region,
                            rule_id="s3-public-access", compliance_frameworks=["aws-cis", "pci-dss"],
                            remediation="Enable all four PublicAccessBlock settings.",
                        ))
                except Exception:
                    findings.append(CloudFindingData(
                        provider="aws", service="s3", category="security", severity="high",
                        title=f"Bucket {name} has no public access block configuration",
                        description=f"Bucket {name} has not configured public access block settings.",
                        resource_id=name, resource_type="bucket", region=r.region,
                        rule_id="s3-no-public-access-block", compliance_frameworks=["aws-cis"],
                        remediation="Configure PublicAccessBlock for the bucket.",
                    ))
                # Encryption
                try:
                    enc = await asyncio.to_thread(s3.get_bucket_encryption, Bucket=name)
                    rules = enc.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
                    if not rules:
                        raise ValueError("no rules")
                except Exception:
                    findings.append(CloudFindingData(
                        provider="aws", service="s3", category="security", severity="medium",
                        title=f"Bucket {name} does not have default encryption enabled",
                        description=f"Bucket {name} does not have server-side encryption configured.",
                        resource_id=name, resource_type="bucket", region=r.region,
                        rule_id="s3-no-encryption", compliance_frameworks=["aws-cis", "pci-dss"],
                        remediation="Enable default bucket encryption with AES-256 or aws:kms.",
                    ))
                # Versioning
                try:
                    ver = await asyncio.to_thread(s3.get_bucket_versioning, Bucket=name)
                    if ver.get("Status") != "Enabled":
                        findings.append(CloudFindingData(
                            provider="aws", service="s3", category="security", severity="low",
                            title=f"Bucket {name} does not have versioning enabled",
                            description=f"Bucket {name} does not have versioning enabled.",
                            resource_id=name, resource_type="bucket", region=r.region,
                            rule_id="s3-no-versioning", compliance_frameworks=["aws-cis"],
                            remediation="Enable bucket versioning for data protection.",
                        ))
                except Exception:
                    pass
                # Logging
                try:
                    log = await asyncio.to_thread(s3.get_bucket_logging, Bucket=name)
                    if not log.get("LoggingEnabled"):
                        findings.append(CloudFindingData(
                            provider="aws", service="s3", category="compliance", severity="low",
                            title=f"Bucket {name} does not have access logging enabled",
                            description=f"Bucket {name} does not have server access logging enabled.",
                            resource_id=name, resource_type="bucket", region=r.region,
                            rule_id="s3-no-logging", compliance_frameworks=["aws-cis"],
                            remediation="Enable server access logging for the bucket.",
                        ))
                except Exception:
                    pass
        except Exception:
            logger.warning("S3 security check failed", exc_info=True)
        return findings
