"""CloudFormation service — orchestrates template preparation and URL generation.

This is the primary entry point for the onboarding wizard. It coordinates:
1. Loading the template from disk
2. Rendering with runtime variables
3. Uploading to S3
4. Generating the CloudFormation Quick Create URL
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import structlog

from app.config import settings
from app.services.cloudformation.s3_service import upload_template
from app.services.cloudformation.template_service import load_template, render_template

logger = structlog.get_logger(__name__)


class CloudFormationServiceError(Exception):
    """Raised when the CloudFormation service encounters an error."""


# Template versioning — increment when template changes
TEMPLATE_VERSION = "v1"
TEMPLATE_FILENAME = f"aws-role-{TEMPLATE_VERSION}.yaml"


def get_template_object_key() -> str:
    """Get the S3 object key for the current template version."""
    return f"{settings.AWS_CONNECT_PREFIX}/{TEMPLATE_FILENAME}"


def prepare_template(
    account_id: str,
    external_id: str,
    role_name: str = "DevarchaiReadOnlyRole",
) -> dict[str, Any]:
    """Load, render, and upload the CloudFormation template.

    This is the main entry point for preparing a CloudFormation template
    for a customer's onboarding session.

    Args:
        account_id: Customer's 12-digit AWS Account ID.
        external_id: Unique external ID for AssumeRole.
        role_name: Name for the IAM role (default: DevarchaiReadOnlyRole).

    Returns:
        Dict with template_url, object_key, and template_content.

    Raises:
        CloudFormationServiceError: If any step fails.
    """
    # Step 1: Load template from disk
    try:
        template_content = load_template(TEMPLATE_FILENAME)
    except Exception as exc:
        raise CloudFormationServiceError(
            f"Failed to load template: {exc}",
        ) from exc

    # Step 2: Render with variables
    variables = {
        "ACCOUNT_ID": account_id,
        "EXTERNAL_ID": external_id,
        "ROLE_NAME": role_name,
        "SCANNER_ROLE_ARN": settings.DEVARCHAI_SCANNER_ARN,
    }

    try:
        rendered = render_template(template_content, variables)
    except Exception as exc:
        raise CloudFormationServiceError(
            f"Failed to render template: {exc}",
        ) from exc

    # Step 3: Upload to S3
    object_key = get_template_object_key()

    try:
        template_url = upload_template(rendered, object_key)
    except Exception as exc:
        raise CloudFormationServiceError(
            f"Failed to upload template to S3: {exc}",
        ) from exc

    logger.info(
        "template_prepared",
        account_id=account_id,
        object_key=object_key,
        template_url=template_url,
    )

    return {
        "template_url": template_url,
        "object_key": object_key,
        "template_content": rendered,
    }


def get_launch_url(
    template_url: str,
    stack_name: str,
) -> str:
    """Generate a CloudFormation Quick Create URL.

    This URL opens the AWS Console with the pre-rendered template
    pre-loaded. All values (External ID, Role Name, Account ID) are
    already baked into the template — the customer only needs to
    click "Create stack" to deploy everything.

    Args:
        template_url: S3 URL of the uploaded (rendered) template.
        stack_name: CloudFormation stack name.

    Returns:
        CloudFormation Console Quick Create URL.
    """
    params = {
        "templateURL": template_url,
        "stackName": stack_name,
    }

    url = (
        "https://console.aws.amazon.com/cloudformation/home"
        f"#/stacks/create/review?{urlencode(params)}"
    )

    logger.debug(
        "launch_url_generated",
        stack_name=stack_name,
        template_url=template_url,
    )

    return url
