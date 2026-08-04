"""AWS onboarding wizard — manages the 4-step connection flow.

Step 1: User provides AWS Account ID + friendly name
Step 2: Backend generates External ID, uploads template to S3, returns CloudFormation URL
Step 3: User launches CloudFormation stack in AWS Console
Step 4: Backend verifies connection via STS AssumeRole
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.services.cloudformation.cloudformation_service import (
    get_launch_url,
    prepare_template,
)

logger = structlog.get_logger(__name__)

# In-memory wizard sessions (production would use Redis)
# Key: wizard_id, Value: WizardSession
_wizard_sessions: dict[str, WizardSession] = {}


@dataclass
class WizardSession:
    """Tracks state for a single onboarding wizard session."""

    wizard_id: str
    user_id: str
    account_id: str
    connection_name: str
    external_id: str
    customer_uuid: str
    stack_name: str
    role_name: str
    template_url: str
    cloudformation_url: str
    role_arn: str | None = None
    status: str = "pending"  # pending | stack_deploying | verifying | verified | failed
    regions: list[str] = field(default_factory=lambda: ["us-east-1"])
    error_message: str | None = None
    verified_account_id: str | None = None
    verified_permissions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "wizard_id": self.wizard_id,
            "account_id": self.account_id,
            "connection_name": self.connection_name,
            "external_id": self.external_id,
            "customer_uuid": self.customer_uuid,
            "stack_name": self.stack_name,
            "role_name": self.role_name,
            "template_url": self.template_url,
            "cloudformation_url": self.cloudformation_url,
            "role_arn": self.role_arn,
            "status": self.status,
            "regions": self.regions,
            "error_message": self.error_message,
            "verified_account_id": self.verified_account_id,
            "verified_permissions": self.verified_permissions,
        }


def _generate_external_id() -> str:
    """Generate a cryptographically random external ID."""
    return secrets.token_hex(16)


def _generate_customer_uuid() -> str:
    """Generate a unique customer identifier."""
    return str(uuid.uuid4())


def init_wizard(
    user_id: str,
    account_id: str,
    connection_name: str = "",
) -> WizardSession:
    """Initialize a new onboarding wizard session.

    Called when user enters their AWS Account ID and clicks Continue.
    Generates all backend-only values, uploads the CloudFormation template
    to S3, and builds the Quick Create URL.

    Raises:
        CloudFormationServiceError: If template preparation fails.
    """
    wizard_id = str(uuid.uuid4())
    external_id = _generate_external_id()
    customer_uuid = _generate_customer_uuid()
    stack_name = f"DevarchaiSecurityStack-{customer_uuid[:8]}"
    role_name = "DevarchaiReadOnlyRole"

    # Prepare template: load from disk → render → upload to S3
    template_result = prepare_template(
        account_id=account_id,
        external_id=external_id,
        role_name=role_name,
    )

    template_url = template_result["template_url"]

    # Build the CloudFormation Quick Create URL
    # Template is pre-rendered — no parameters needed in the URL
    cloudformation_url = get_launch_url(
        template_url=template_url,
        stack_name=stack_name,
    )

    session = WizardSession(
        wizard_id=wizard_id,
        user_id=user_id,
        account_id=account_id,
        connection_name=connection_name or f"AWS ({account_id})",
        external_id=external_id,
        customer_uuid=customer_uuid,
        stack_name=stack_name,
        role_name=role_name,
        template_url=template_url,
        cloudformation_url=cloudformation_url,
    )

    _wizard_sessions[wizard_id] = session

    logger.info(
        "wizard_initialized",
        wizard_id=wizard_id,
        user_id=user_id,
        account_id=account_id,
        template_url=template_url,
    )

    return session


def get_wizard(wizard_id: str) -> WizardSession | None:
    """Get a wizard session by ID."""
    return _wizard_sessions.get(wizard_id)


def update_wizard_status(
    wizard_id: str,
    status: str,
    error_message: str | None = None,
) -> WizardSession | None:
    """Update wizard status."""
    session = _wizard_sessions.get(wizard_id)
    if session:
        session.status = status
        if error_message:
            session.error_message = error_message
    return session


def verify_connection(wizard_id: str) -> dict[str, Any]:
    """Verify the AWS connection after CloudFormation stack is deployed.

    The backend runs as the scanner identity (DevArchAIScanner role or
    IAM user). A single AssumeRole call goes directly to the customer's
    role in their account. Validates account ID, permissions, and regions.
    """
    from app.cloud.aws.sts import STSAssumeRoleError, assume_customer_role

    session = _wizard_sessions.get(wizard_id)
    if not session:
        return {"success": False, "error": "Wizard session not found"}

    session.status = "verifying"

    role_arn = f"arn:aws:iam::{session.account_id}:role/{session.role_name}"
    session.role_arn = role_arn

    try:
        # Direct AssumeRole: backend's execution role → customer role
        assumed_session = assume_customer_role(
            customer_account_id=session.account_id,
            customer_role_name=session.role_name,
            external_id=session.external_id,
            session_name=f"devarchai-verify-{session.account_id}",
        )

        # Verify identity
        sts_assumed = assumed_session.client("sts")
        identity = sts_assumed.get_caller_identity()
        verified_account_id = identity["Account"]

        if verified_account_id != session.account_id:
            session.status = "failed"
            session.error_message = (
                f"Account mismatch: expected {session.account_id}, "
                f"got {verified_account_id}"
            )
            return {"success": False, "error": session.error_message}

        session.verified_account_id = verified_account_id

        # Check permissions
        permissions = _check_permissions(assumed_session)
        session.verified_permissions = permissions["available"]

        # Check regions
        ec2 = assumed_session.client("ec2", region_name="us-east-1")
        regions_response = ec2.describe_regions()
        session.regions = [r["RegionName"] for r in regions_response["Regions"]]

        session.status = "verified"

        logger.info(
            "wizard_verified",
            wizard_id=wizard_id,
            account_id=session.account_id,
            permissions=len(permissions["available"]),
            regions=len(session.regions),
        )

        return {
            "success": True,
            "account_id": verified_account_id,
            "role_arn": role_arn,
            "permissions": permissions,
            "regions": session.regions,
        }

    except STSAssumeRoleError as exc:
        session.status = "failed"
        session.error_message = exc.message
        logger.error(
            "wizard_verify_failed",
            wizard_id=wizard_id,
            error_type=exc.error_type,
            error=exc.message,
            details=exc.details,
        )
        return {"success": False, "error": exc.message, "error_type": exc.error_type}

    except Exception as exc:
        session.status = "failed"
        session.error_message = f"Verification failed: {exc}"
        logger.error("wizard_verify_error", wizard_id=wizard_id, error=str(exc))
        return {"success": False, "error": session.error_message}


def _check_permissions(session: Any) -> dict[str, Any]:
    """Check which required permissions are available."""
    required = {
        "ec2:DescribeInstances": "EC2",
        "s3:ListAllMyBuckets": "S3",
        "rds:DescribeDBInstances": "RDS",
        "iam:ListUsers": "IAM",
        "lambda:ListFunctions": "Lambda",
        "eks:ListClusters": "EKS",
        "elasticloadbalancing:DescribeLoadBalancers": "ELB",
        "ce:GetCostAndUsage": "Cost Explorer",
        "cloudwatch:GetMetricData": "CloudWatch",
        "cloudtrail:DescribeTrails": "CloudTrail",
        "organizations:ListAccounts": "Organizations",
        "support:DescribeTrustedAdvisorChecks": "Support",
    }

    available = []
    unavailable = []

    for action, service in required.items():
        try:
            iam = session.client("iam")
            # Simulate the permission
            response = iam.simulate_principal_policy(
                PolicySourceArn=session.client("sts").get_caller_identity()["Arn"],
                ActionNames=[action],
            )
            eval_result = response["EvaluationResults"][0]["EvalDecision"]
            if eval_result == "allowed":
                available.append(service)
            else:
                unavailable.append(service)
        except Exception:
            unavailable.append(service)

    return {
        "available": available,
        "unavailable": unavailable,
        "total": len(required),
    }


def complete_wizard(wizard_id: str) -> WizardSession | None:
    """Mark wizard as complete and return the session."""
    session = _wizard_sessions.get(wizard_id)
    if session and session.status == "verified":
        session.status = "completed"
        # Clean up from memory
        _wizard_sessions.pop(wizard_id, None)
    return session


def cleanup_expired_wizards(max_age_seconds: int = 3600) -> int:
    """Clean up wizard sessions older than max_age_seconds."""
    # In production, this would be handled by Redis TTL
    # For now, this is a no-op placeholder
    return 0
