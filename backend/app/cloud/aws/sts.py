"""Shared STS helpers for cross-account access.

Architecture:
  Backend runs AS the scanner identity (ECS task role / instance profile).
  The only AssumeRole call is: scanner identity → customer role.

  Production: ECS task role IS DevArchAIScanner → boto3 uses it automatically
  Dev: IAM user credentials in .env → boto3 uses them directly
"""

from __future__ import annotations

import sys
from typing import Any

import boto3
import structlog
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings

logger = structlog.get_logger(__name__)


class STSAssumeRoleError(Exception):
    """Raised when cross-account AssumeRole fails."""

    def __init__(self, error_type: str, message: str, details: dict[str, Any] | None = None):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(message)


def get_caller_identity() -> dict[str, str]:
    """Get the current IAM caller identity with full diagnostics.

    Returns:
        Dict with account, arn, user_id, role_name, credential_source.
    """
    sts = boto3.client("sts")
    identity = sts.get_caller_identity()
    arn = identity["Arn"]

    # Determine credential source and role name from ARN
    parts = arn.split(":")
    resource = parts[5] if len(parts) > 5 else ""
    resource_type = resource.split("/")[0] if "/" in resource else ""
    resource_name = resource.split("/", 1)[1] if "/" in resource else resource

    # Determine credential source
    if ":root" in arn:
        credential_source = "root_account"
    elif ":user/" in arn:
        credential_source = "iam_user"
    elif ":role/" in arn:
        credential_source = "iam_role_assumed"
    elif ":assumed-role/" in arn:
        credential_source = "assumed_role"
    else:
        credential_source = "unknown"

    return {
        "account": identity["Account"],
        "arn": arn,
        "user_id": identity["UserId"],
        "role_name": resource_name,
        "resource_type": resource_type,
        "credential_source": credential_source,
    }


def validate_startup_identity() -> None:
    """Validate the backend's AWS identity at startup.

    - Logs full identity diagnostics (account, ARN, credential source, role name)
    - Fails with sys.exit(1) if running as root account
    """
    try:
        identity = get_caller_identity()
    except Exception as exc:
        logger.warning("startup_identity_check_failed", error=str(exc))
        return

    is_root = identity["credential_source"] == "root_account"

    if is_root:
        logger.critical(
            "ROOT_ACCOUNT_DETECTED",
            message=(
                "Backend is running as the AWS root account. "
                "Root credentials are not supported. "
                "Configure an IAM user or role with DevArchAI Scanner permissions. "
                "See: https://docs.devarchai.com/aws-onboarding"
            ),
            arn=identity["arn"],
            account=identity["account"],
        )
        sys.exit(1)

    logger.info(
        "aws_identity_validated",
        account=identity["account"],
        arn=identity["arn"],
        role_name=identity["role_name"],
        resource_type=identity["resource_type"],
        credential_source=identity["credential_source"],
        scanner_arn=settings.DEVARCHAI_SCANNER_ARN,
    )

    if identity["credential_source"] == "iam_user":
        logger.warning(
            "IAM_USER_CREDENTIALS",
            message=(
                "Backend is using IAM user credentials. "
                "In production, use an ECS task role or instance profile instead."
            ),
            user=identity["role_name"],
        )


def assume_customer_role(
    customer_account_id: str,
    customer_role_name: str,
    external_id: str,
    session_name: str = "devarchai-customer",
) -> boto3.Session:
    """Assume a customer's IAM role directly.

    The backend's execution role (DevArchAIScanner) assumes the customer's role.
    boto3 uses the default credential provider chain to get the execution role.

    Args:
        customer_account_id: Customer's 12-digit AWS Account ID.
        customer_role_name: Name of the role in the customer's account.
        external_id: The external ID for the AssumeRole condition.
        session_name: Name for the STS session.

    Returns:
        boto3.Session configured with the customer's temporary credentials.

    Raises:
        STSAssumeRoleError: With specific error_type for each failure mode:
            - AccessDenied: Trust policy doesn't match or External ID wrong
            - RoleNotFound: Role doesn't exist in customer account
            - InvalidExternalId: External ID doesn't match
            - ValidationError: Malformed ARN
    """
    customer_role_arn = f"arn:aws:iam::{customer_account_id}:role/{customer_role_name}"

    # Direct AssumeRole: backend's execution role → customer role
    try:
        sts = boto3.client("sts")
        result = sts.assume_role(
            RoleArn=customer_role_arn,
            RoleSessionName=session_name,
            ExternalId=external_id,
            DurationSeconds=3600,
        )

        credentials = result["Credentials"]
        session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

        logger.info(
            "customer_role_assumed",
            role_arn=customer_role_arn,
            session_name=session_name,
        )
        return session

    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        error_msg = exc.response["Error"]["Message"]

        logger.error(
            "customer_role_assume_failed",
            role_arn=customer_role_arn,
            error_code=error_code,
            error_message=error_msg,
        )

        if error_code == "AccessDenied":
            if "not authorized to perform: sts:AssumeRole" in error_msg:
                raise STSAssumeRoleError(
                    error_type="AccessDenied",
                    message=(
                        "Cannot assume the IAM role. Ensure the CloudFormation stack "
                        "was created successfully, the role exists, and the trust "
                        f"policy allows: {settings.DEVARCHAI_SCANNER_ARN}"
                    ),
                    details={
                        "role_arn": customer_role_arn,
                        "error_code": error_code,
                        "scanner_arn": settings.DEVARCHAI_SCANNER_ARN,
                    },
                ) from exc
            raise STSAssumeRoleError(
                error_type="AccessDenied",
                message=f"Access denied: {error_msg}",
                details={"role_arn": customer_role_arn, "error_code": error_code},
            ) from exc

        if error_code == "NoSuchEntity":
            raise STSAssumeRoleError(
                error_type="RoleNotFound",
                message=(
                    f"Role '{customer_role_name}' not found in account "
                    f"'{customer_account_id}'. Please ensure the CloudFormation "
                    "stack has been created successfully."
                ),
                details={"role_arn": customer_role_arn, "error_code": error_code},
            ) from exc

        if error_code == "InvalidExternalId":
            raise STSAssumeRoleError(
                error_type="InvalidExternalId",
                message=(
                    "The External ID is invalid or does not match. "
                    "Please ensure you are using the latest connection details."
                ),
                details={"role_arn": customer_role_arn, "error_code": error_code},
            ) from exc

        if error_code == "ValidationError":
            raise STSAssumeRoleError(
                error_type="ValidationError",
                message=f"Invalid role ARN: {customer_role_arn}. Check the account ID and role name.",
                details={"role_arn": customer_role_arn, "error_code": error_code},
            ) from exc

        raise STSAssumeRoleError(
            error_type="AssumeRoleFailed",
            message=f"AWS error: {error_msg}",
            details={"role_arn": customer_role_arn, "error_code": error_code},
        ) from exc

    except (BotoCoreError, Exception) as exc:
        logger.error("customer_role_assume_error", error=str(exc))
        raise STSAssumeRoleError(
            error_type="AssumeRoleError",
            message=f"Unexpected error assuming customer role: {exc}",
        ) from exc
