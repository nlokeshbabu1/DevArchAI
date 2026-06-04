"""AWS security analysis service."""

from __future__ import annotations

import structlog

from app.services.aws.aws_client import AWSIntegrationError, call_aws, client, enabled_regions

logger = structlog.get_logger(__name__)


class AWSSecurityService:
    """Detect AWS security posture findings."""

    async def analyze(self, session, default_region: str) -> list[dict]:
        regions = await enabled_regions(session, default_region)
        findings = []
        findings.extend(await self._check_s3_public(session, default_region))
        findings.extend(await self._check_iam_account(session, default_region))
        for region in regions:
            findings.extend(await self._check_security_groups(session, region))
            findings.extend(await self._check_ebs_encryption(session, region))
            findings.extend(await self._check_public_rds(session, region))
        return findings

    def _finding(self, severity, title, description, resource_type=None, resource_id=None, region=None, recommendation=None, metadata=None):
        return {"category": "security", "severity": severity, "title": title, "description": description, "resource_type": resource_type, "resource_id": resource_id, "region": region, "recommendation": recommendation, "metadata": metadata or {}}

    async def _check_s3_public(self, session, region: str) -> list[dict]:
        s3 = client(session, "s3", region)
        findings = []
        try:
            buckets = await call_aws(s3.list_buckets)
            for bucket in buckets.get("Buckets", []):
                name = bucket["Name"]
                try:
                    policy_status = await call_aws(s3.get_bucket_policy_status, Bucket=name)
                    if policy_status.get("PolicyStatus", {}).get("IsPublic"):
                        findings.append(self._finding("critical", "Public S3 bucket policy", f"S3 bucket {name} has a public policy.", "s3", name, "aws-global", "Restrict bucket policy and block public access."))
                except AWSIntegrationError:
                    pass
                try:
                    acl = await call_aws(s3.get_bucket_acl, Bucket=name)
                    public_grants = [grant for grant in acl.get("Grants", []) if "AllUsers" in str(grant) or "AuthenticatedUsers" in str(grant)]
                    if public_grants:
                        findings.append(self._finding("high", "Public S3 bucket ACL", f"S3 bucket {name} has public ACL grants.", "s3", name, "aws-global", "Remove public ACL grants and enable bucket-owner-enforced object ownership."))
                except AWSIntegrationError:
                    pass
        except AWSIntegrationError as exc:
            logger.warning("AWS S3 security checks failed", error=str(exc))
        return findings

    async def _check_security_groups(self, session, region: str) -> list[dict]:
        ec2 = client(session, "ec2", region)
        findings = []
        try:
            response = await call_aws(ec2.describe_security_groups)
            for group in response.get("SecurityGroups", []):
                for rule in group.get("IpPermissions", []):
                    for ip_range in rule.get("IpRanges", []):
                        if ip_range.get("CidrIp") == "0.0.0.0/0":
                            port = rule.get("FromPort", "all")
                            severity = "critical" if port in (22, 3389, "all") else "high"
                            findings.append(self._finding(severity, "Security group open to internet", f"{group['GroupId']} allows inbound access from 0.0.0.0/0 on port {port}.", "security_group", group["GroupId"], region, "Restrict ingress CIDRs to trusted networks."))
        except AWSIntegrationError as exc:
            logger.warning("AWS security group checks failed", region=region, error=str(exc))
        return findings

    async def _check_iam_account(self, session, region: str) -> list[dict]:
        iam = client(session, "iam", region)
        findings = []
        try:
            summary = await call_aws(iam.get_account_summary)
            values = summary.get("SummaryMap", {})
            if values.get("AccountMFAEnabled", 0) == 0:
                findings.append(self._finding("critical", "Root MFA disabled", "AWS root account MFA is not enabled.", "iam_account", "root", "aws-global", "Enable hardware or virtual MFA for the AWS root account."))
            if values.get("AccountAccessKeysPresent", 0):
                findings.append(self._finding("critical", "Root access key present", "AWS root account has active access keys.", "iam_account", "root", "aws-global", "Delete root access keys and use IAM roles."))
        except AWSIntegrationError as exc:
            logger.warning("AWS IAM account checks failed", error=str(exc))
        return findings

    async def _check_ebs_encryption(self, session, region: str) -> list[dict]:
        ec2 = client(session, "ec2", region)
        findings = []
        try:
            volumes = await call_aws(ec2.describe_volumes)
            for volume in volumes.get("Volumes", []):
                if not volume.get("Encrypted"):
                    findings.append(self._finding("medium", "Unencrypted EBS volume", f"EBS volume {volume['VolumeId']} is not encrypted.", "ebs_volume", volume["VolumeId"], region, "Migrate data to an encrypted volume."))
        except AWSIntegrationError as exc:
            logger.warning("AWS EBS encryption checks failed", region=region, error=str(exc))
        return findings

    async def _check_public_rds(self, session, region: str) -> list[dict]:
        rds = client(session, "rds", region)
        findings = []
        try:
            dbs = await call_aws(rds.describe_db_instances)
            for db in dbs.get("DBInstances", []):
                if db.get("PubliclyAccessible"):
                    findings.append(self._finding("high", "Public RDS instance", f"RDS instance {db['DBInstanceIdentifier']} is publicly accessible.", "rds", db["DBInstanceIdentifier"], region, "Disable public accessibility and place the database in private subnets."))
        except AWSIntegrationError as exc:
            logger.warning("AWS RDS public checks failed", region=region, error=str(exc))
        return findings
