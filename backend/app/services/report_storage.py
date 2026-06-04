"""S3-backed storage for generated reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import boto3
import structlog
from botocore.config import Config

from app.config import settings

logger = structlog.get_logger(__name__)

PDF_CONTENT_TYPE = "application/pdf"
EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PRESIGNED_URL_EXPIRY_SECONDS = 300


class ReportStorage:
    """Upload report artifacts to private S3 and generate presigned URLs."""

    def __init__(
        self,
        bucket_name: str = settings.S3_BUCKET_NAME,
        region_name: str = settings.AWS_REGION,
        aws_access_key_id: str | None = settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key: str | None = settings.AWS_SECRET_ACCESS_KEY,
        aws_session_token: str | None = settings.AWS_SESSION_TOKEN,
        s3_client: Any | None = None,
    ) -> None:
        self.bucket_name = bucket_name
        self.region_name = region_name
        if s3_client is not None:
            self._s3_client = s3_client
            return

        session_kwargs: dict[str, Any] = {"region_name": region_name}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key
            if aws_session_token:
                session_kwargs["aws_session_token"] = aws_session_token

        session = boto3.session.Session(**session_kwargs)
        self._s3_client = session.client(
            "s3",
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

    def build_object_key(self, *, user_id: str | None, scan_id: str, format: str) -> str:
        """Build the canonical S3 object key for a scan report artifact."""
        user_segment = user_id or "anonymous"
        file_name = "report.pdf" if format == "pdf" else "report.xlsx"
        return f"reports/{user_segment}/{scan_id}/{file_name}"

    def upload_bytes(
        self,
        *,
        content: bytes,
        key: str,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Upload report bytes without exposing the object publicly."""
        self._s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content,
            ContentType=content_type,
            Metadata=metadata or {},
            ServerSideEncryption="AES256",
        )
        logger.info("Report uploaded to S3", bucket=self.bucket_name, key=key)

    def upload_file(
        self,
        *,
        file_path: str,
        key: str,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Upload a locally generated report file to S3."""
        self.upload_bytes(
            content=Path(file_path).read_bytes(),
            key=key,
            content_type=content_type,
            metadata=metadata,
        )

    def generate_presigned_download_url(
        self,
        *,
        key: str,
        filename: str,
        expires_in: int = PRESIGNED_URL_EXPIRY_SECONDS,
    ) -> str:
        """Create a short-lived presigned download URL for a private report object."""
        return self._s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": key,
                "ResponseContentDisposition": f'attachment; filename="{filename}"',
            },
            ExpiresIn=expires_in,
        )
