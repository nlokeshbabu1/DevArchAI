"""AWS IAM analysis service."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from app.services.aws.aws_client import AWSIntegrationError, call_aws, client

logger = structlog.get_logger(__name__)


class AWSIAMService:
    """Analyze IAM permissions and identity hygiene."""

    async def analyze(self, session, default_region: str) -> list[dict]:
        iam = client(session, "iam", default_region)
        findings = []
        try:
            users = await call_aws(iam.list_users)
            for user in users.get("Users", []):
                findings.extend(await self._analyze_user(iam, user))

            roles = await call_aws(iam.list_roles)
            for role in roles.get("Roles", []):
                findings.extend(await self._analyze_role(iam, role))
        except AWSIntegrationError as exc:
            logger.warning("AWS IAM analysis failed", error=str(exc))
        return findings

    def _finding(self, severity, title, description, resource_type, resource_id, recommendation, metadata=None):
        return {"category": "iam", "severity": severity, "title": title, "description": description, "resource_type": resource_type, "resource_id": resource_id, "region": "aws-global", "recommendation": recommendation, "metadata": metadata or {}}

    async def _analyze_user(self, iam, user: dict) -> list[dict]:
        name = user["UserName"]
        findings = []
        try:
            attached = await call_aws(iam.list_attached_user_policies, UserName=name)
            for policy in attached.get("AttachedPolicies", []):
                if policy.get("PolicyArn") == "arn:aws:iam::aws:policy/AdministratorAccess":
                    findings.append(self._finding("high", "IAM user has administrator access", f"IAM user {name} has AdministratorAccess.", "iam_user", name, "Use least privilege or a scoped role."))

            keys = await call_aws(iam.list_access_keys, UserName=name)
            now = datetime.now(UTC)
            for key in keys.get("AccessKeyMetadata", []):
                age_days = (now - key["CreateDate"]).days
                if age_days > 90:
                    findings.append(self._finding("medium", "Old IAM access key", f"Access key for {name} is {age_days} days old.", "iam_user", name, "Rotate access keys at least every 90 days.", {"access_key_id": key.get("AccessKeyId")[-4:]}))

            last_used = user.get("PasswordLastUsed")
            if not last_used or (now - last_used).days > 90:
                findings.append(self._finding("low", "Inactive IAM user", f"IAM user {name} has no recent console activity.", "iam_user", name, "Disable or remove inactive IAM users."))
        except AWSIntegrationError as exc:
            logger.warning("AWS IAM user analysis failed", user=name, error=str(exc))
        return findings

    async def _analyze_role(self, iam, role: dict) -> list[dict]:
        name = role["RoleName"]
        findings = []
        try:
            attached = await call_aws(iam.list_attached_role_policies, RoleName=name)
            if not attached.get("AttachedPolicies") and (datetime.now(UTC) - role["CreateDate"]).days > 90:
                findings.append(self._finding("low", "Unused IAM role candidate", f"IAM role {name} has no attached managed policies.", "iam_role", name, "Review and remove unused roles."))
            for policy in attached.get("AttachedPolicies", []):
                if policy.get("PolicyArn") == "arn:aws:iam::aws:policy/AdministratorAccess":
                    findings.append(self._finding("high", "IAM role has administrator access", f"IAM role {name} has AdministratorAccess.", "iam_role", name, "Scope role permissions to required services."))
        except AWSIntegrationError as exc:
            logger.warning("AWS IAM role analysis failed", role=name, error=str(exc))
        return findings
