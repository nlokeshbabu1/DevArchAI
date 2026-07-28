"""IAM scanner — users, roles, policies, access keys, MFA."""

from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import UTC, datetime
from typing import Any

from app.cloud.base import BaseCloudScanner, CloudFindingData, CloudResourceData

logger = logging.getLogger(__name__)


class IAMScanner(BaseCloudScanner):
    service_name = "iam"

    async def scan(self, session: Any, regions: list[str]) -> list[CloudResourceData]:
        resources: list[CloudResourceData] = []
        try:
            iam = session.client("iam")

            # ListUsers
            for page in await self._paginate(iam, "list_users"):
                users = page.get("Users", [])
                for user in users:
                    resources.append(CloudResourceData(
                        provider="aws", service="iam",
                        resource_id=user["UserId"], resource_name=user["UserName"],
                        resource_type="user", region="global", status="active",
                        configuration={"arn": user.get("Arn"), "path": user.get("Path")},
                        created_at=user.get("CreateDate"),
                    ))
            user_count = len([r for r in resources if r.resource_type == "user"])
            logger.info("IAM ListUsers: service=iam api=ListUsers found=%d", user_count)

            # ListRoles
            for page in await self._paginate(iam, "list_roles"):
                roles = page.get("Roles", [])
                for role in roles:
                    resources.append(CloudResourceData(
                        provider="aws", service="iam",
                        resource_id=role["RoleId"], resource_name=role["RoleName"],
                        resource_type="role", region="global", status="active",
                        configuration={
                            "arn": role.get("Arn"), "path": role.get("Path"),
                            "max_session_duration": role.get("MaxSessionDuration"),
                            "assume_role_policy": role.get("AssumeRolePolicyDocument"),
                        },
                        created_at=role.get("CreateDate"),
                    ))
            role_count = len([r for r in resources if r.resource_type == "role"])
            logger.info("IAM ListRoles: service=iam api=ListRoles found=%d", role_count)

            # ListPolicies
            for page in await self._paginate(iam, "list_policies", Scope="Local"):
                policies = page.get("Policies", [])
                for policy in policies:
                    resources.append(CloudResourceData(
                        provider="aws", service="iam",
                        resource_id=policy["PolicyId"], resource_name=policy["PolicyName"],
                        resource_type="policy", region="global", status="active",
                        configuration={"arn": policy.get("Arn")},
                        created_at=policy.get("CreateDate"),
                    ))
            policy_count = len([r for r in resources if r.resource_type == "policy"])
            logger.info("IAM ListPolicies: service=iam api=ListPolicies found=%d", policy_count)

            logger.info("IAM scan_complete: service=iam total_resources=%d", len(resources))
        except Exception:
            tb = traceback.format_exc()
            logger.warning("IAM scan failed\n%s", tb)
        return resources

    async def check_security(self, session: Any, resources: list[CloudResourceData]) -> list[CloudFindingData]:
        findings: list[CloudFindingData] = []
        try:
            iam = session.client("iam")
            for r in resources:
                if r.resource_type == "user":
                    findings.extend(await self._check_user(iam, r))
        except Exception:
            logger.warning("IAM security check failed", exc_info=True)
        return findings

    async def _check_user(self, iam: Any, r: CloudResourceData) -> list[CloudFindingData]:
        findings: list[CloudFindingData] = []
        mfa = await asyncio.to_thread(iam.list_mfa_devices, UserName=r.resource_name)
        if not mfa.get("MFADevices"):
            findings.append(CloudFindingData(
                provider="aws", service="iam", category="security", severity="high",
                title=f"IAM user {r.resource_name} has no MFA enabled",
                description=f"User {r.resource_name} does not have multi-factor authentication enabled.",
                resource_id=r.resource_id, resource_type=r.resource_type, region="global",
                rule_id="iam-no-mfa", compliance_frameworks=["aws-cis", "pci-dss"],
                remediation="Enable MFA for the user.",
            ))
        keys = await asyncio.to_thread(iam.list_access_keys, UserName=r.resource_name)
        for key in keys.get("AccessKeyMetadata", []):
            age_days = (datetime.now(UTC) - key["CreateDate"]).days
            if age_days > 90:
                findings.append(CloudFindingData(
                    provider="aws", service="iam", category="security", severity="medium",
                    title=f"Access key for {r.resource_name} is {age_days} days old",
                    description=f"Access key {key['AccessKeyId']} is {age_days} days old.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region="global",
                    rule_id="iam-old-access-key", compliance_frameworks=["aws-cis"],
                    remediation="Rotate the access key.",
                ))
        attached = await asyncio.to_thread(iam.list_attached_user_policies, UserName=r.resource_name)
        for policy in attached.get("AttachedPolicies", []):
            if "AdminAccess" in policy.get("PolicyName", ""):
                findings.append(CloudFindingData(
                    provider="aws", service="iam", category="security", severity="critical",
                    title=f"User {r.resource_name} has AdministratorAccess",
                    description=f"User {r.resource_name} has the AdministratorAccess policy attached.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region="global",
                    rule_id="iam-admin-user", compliance_frameworks=["aws-cis"],
                    remediation="Follow the principle of least privilege.",
                ))
        return findings

    async def _paginate(self, client: Any, method: str, **kwargs: Any) -> list[dict[str, Any]]:
        paginator = await asyncio.to_thread(client.get_paginator, method)
        pages: list[dict[str, Any]] = []
        for page in paginator.paginate(**kwargs):
            pages.append(page)
        return pages
