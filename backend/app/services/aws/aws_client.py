"""AWS boto3 client helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.encryption import get_encryption_service
from app.models.aws import AWSAccount


AWS_CONFIG = Config(retries={"max_attempts": 6, "mode": "adaptive"}, user_agent_extra="DevArchAI/aws-integration")


@dataclass
class AWSCredentials:
    access_key_id: str
    secret_access_key: str
    region: str


class AWSIntegrationError(Exception):
    """AWS integration error safe to expose without secret data."""


def decrypt_account_credentials(account: AWSAccount) -> AWSCredentials:
    encryption = get_encryption_service()
    return AWSCredentials(
        access_key_id=encryption.decrypt(account.access_key_id_encrypted or ""),
        secret_access_key=encryption.decrypt(account.secret_access_key_encrypted or ""),
        region=account.default_region or "us-east-1",
    )


def build_session(credentials: AWSCredentials) -> boto3.Session:
    return boto3.Session(
        aws_access_key_id=credentials.access_key_id,
        aws_secret_access_key=credentials.secret_access_key,
        region_name=credentials.region,
    )


def client(session: boto3.Session, service: str, region: str | None = None):
    return session.client(service, region_name=region or session.region_name or "us-east-1", config=AWS_CONFIG)


async def call_aws(func, *args, **kwargs) -> Any:
    try:
        return await asyncio.to_thread(func, *args, **kwargs)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "AWSClientError")
        raise AWSIntegrationError(code) from exc
    except BotoCoreError as exc:
        raise AWSIntegrationError(exc.__class__.__name__) from exc


async def validate_credentials(access_key_id: str, secret_access_key: str, region: str) -> dict[str, str]:
    session = build_session(AWSCredentials(access_key_id, secret_access_key, region))
    sts = client(session, "sts", region)
    identity = await call_aws(sts.get_caller_identity)
    return {
        "account_id": identity["Account"],
        "arn": identity["Arn"],
        "user_id": identity["UserId"],
    }


async def enabled_regions(session: boto3.Session, fallback_region: str) -> list[str]:
    ec2 = client(session, "ec2", fallback_region)
    try:
        response = await call_aws(ec2.describe_regions, AllRegions=False)
        return [region["RegionName"] for region in response.get("Regions", [])]
    except AWSIntegrationError:
        return [fallback_region]
