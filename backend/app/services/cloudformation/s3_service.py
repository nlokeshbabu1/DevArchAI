"""S3 operations for CloudFormation template storage.

Handles uploading templates to S3, generating presigned URLs,
and validating bucket accessibility.
"""

from __future__ import annotations

from typing import Any

import boto3
import structlog
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings

logger = structlog.get_logger(__name__)

_S3_CONFIG = Config(
    retries={"max_attempts": 3, "mode": "adaptive"},
    user_agent_extra="DevArchAI/cloudformation",
)

# Module-level S3 client (initialized lazily)
_s3_client: Any = None


class S3UploadError(Exception):
    """Raised when S3 operations fail."""


def _get_s3_client():
    """Get or create the S3 client using platform credentials."""
    global _s3_client
    if _s3_client is None:
        kwargs: dict[str, str] = {"region_name": settings.AWS_REGION}
        if settings.AWS_ACCESS_KEY_ID:
            kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        if settings.AWS_SECRET_ACCESS_KEY:
            kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        if settings.AWS_SESSION_TOKEN:
            kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN

        session = boto3.Session(**kwargs)
        _s3_client = session.client("s3", config=_S3_CONFIG)
    return _s3_client


def validate_bucket(bucket_name: str | None = None) -> bool:
    """Validate that the S3 bucket exists and is accessible.

    Args:
        bucket_name: Bucket to validate. Defaults to AWS_CONNECT_BUCKET.

    Returns:
        True if bucket is accessible.

    Raises:
        S3UploadError: If bucket doesn't exist or is inaccessible.
    """
    bucket = bucket_name or settings.AWS_CONNECT_BUCKET
    s3 = _get_s3_client()

    try:
        s3.head_bucket(Bucket=bucket)
        logger.debug("bucket_validated", bucket=bucket)
        return True
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code == "404":
            raise S3UploadError(f"Bucket not found: {bucket}") from exc
        if error_code == "403":
            raise S3UploadError(f"Access denied to bucket: {bucket}") from exc
        raise S3UploadError(f"Bucket validation failed: {exc}") from exc
    except (BotoCoreError, Exception) as exc:
        raise S3UploadError(f"Bucket validation failed: {exc}") from exc


def upload_template(
    template_content: str,
    object_key: str,
    bucket_name: str | None = None,
) -> str:
    """Upload a rendered CloudFormation template to S3.

    Args:
        template_content: Rendered template content (YAML string).
        object_key: S3 object key (e.g., "cloudformation/aws-role-v1.yaml").
        bucket_name: Target bucket. Defaults to AWS_CONNECT_BUCKET.

    Returns:
        The S3 object URL (https://bucket.s3.region.amazonaws.com/key).

    Raises:
        S3UploadError: If upload fails.
    """
    bucket = bucket_name or settings.AWS_CONNECT_BUCKET
    s3 = _get_s3_client()

    try:
        s3.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=template_content.encode("utf-8"),
            ContentType="application/x-yaml",
            ServerSideEncryption="AES256",
        )
    except (BotoCoreError, ClientError) as exc:
        raise S3UploadError(f"Failed to upload template to S3: {exc}") from exc

    url = get_template_url(object_key, bucket)

    logger.info(
        "template_uploaded",
        bucket=bucket,
        key=object_key,
        size_bytes=len(template_content),
    )

    return url


def get_template_url(object_key: str, bucket_name: str | None = None) -> str:
    """Generate the public HTTPS URL for a CloudFormation template in S3.

    Templates in the cloudformation/ prefix are publicly readable so
    CloudFormation can fetch them without presigned URLs. Presigned URLs
    break when embedded in CloudFormation Quick Create URLs due to
    URL-encoding conflicts.

    Args:
        object_key: S3 object key.
        bucket_name: Bucket name. Defaults to AWS_CONNECT_BUCKET.

    Returns:
        HTTPS URL to the template object.
    """
    bucket = bucket_name or settings.AWS_CONNECT_BUCKET
    region = settings.AWS_REGION
    return f"https://{bucket}.s3.{region}.amazonaws.com/{object_key}"
