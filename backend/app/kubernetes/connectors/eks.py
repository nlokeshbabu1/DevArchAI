"""Amazon EKS cluster connector — reuses existing AWS CloudConnection."""

from __future__ import annotations

import base64
from typing import Any

import structlog
from botocore.signers import RequestSigner

from app.kubernetes.connectors.base import ClusterConnector
from app.kubernetes.validator import validate_api_client
from app.kubernetes.types import ConnectionStatus, ValidationResult

logger = structlog.get_logger(__name__)


def _generate_eks_token(cluster_name: str, region: str, session: Any) -> str:
    """Generate a bearer token for EKS API authentication."""
    sts_client = session.client("sts", region_name=region)
    service_id = sts_client.meta.service_model.service_id
    signer = RequestSigner(
        service_id,
        region,
        "sts",
        "v4",
        session.get_credentials(),
        session.events,
    )
    url = f"https://sts.{region}.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15"
    signed_url = signer.generate_presigned_url(
        {
            "method": "GET",
            "url": url,
            "body": {},
            "headers": {"x-k8s-aws-id": cluster_name},
            "context": {},
        },
        region=region,
        expires_in=60,
        operation_name="",
    )
    token = "k8s-aws-v1." + base64.urlsafe_b64encode(signed_url.encode()).decode().rstrip("=")
    return token


class EksConnector(ClusterConnector):
    """Connect to EKS using STS credentials from an existing AWS connection."""

    def __init__(
        self,
        *,
        cluster_name: str,
        region: str,
        aws_session: Any,
        cluster_endpoint: str | None = None,
        ca_data: str | None = None,
    ) -> None:
        self._cluster_name = cluster_name
        self._region = region
        self._aws_session = aws_session
        self._cluster_endpoint = cluster_endpoint
        self._ca_data = ca_data
        self._api_client: Any = None
        self._kubernetes_version: str | None = None

    @property
    def provider_label(self) -> str:
        return "AWS EKS"

    def _describe_cluster(self) -> dict[str, Any]:
        eks = self._aws_session.client("eks", region_name=self._region)
        response = eks.describe_cluster(name=self._cluster_name)
        return response.get("cluster", {})

    def _load_client(self) -> Any:
        if self._api_client is not None:
            return self._api_client

        from kubernetes import client

        cluster = self._describe_cluster()
        endpoint = self._cluster_endpoint or cluster.get("endpoint")
        ca_data = self._ca_data or (cluster.get("certificateAuthority") or {}).get("data")
        self._kubernetes_version = cluster.get("version")
        self._cluster_endpoint = endpoint

        if not endpoint or not ca_data:
            raise ValueError("EKS cluster endpoint or CA data unavailable")

        token = _generate_eks_token(self._cluster_name, self._region, self._aws_session)

        configuration = client.Configuration()
        configuration.host = endpoint
        configuration.api_key = {"authorization": f"Bearer {token}"}
        configuration.verify_ssl = True
        configuration.ssl_ca_cert = None

        import tempfile

        ca_file = tempfile.NamedTemporaryFile(delete=False, suffix=".crt")
        try:
            ca_file.write(base64.b64decode(ca_data))
            ca_file.flush()
            ca_file.close()
            configuration.ssl_ca_cert = ca_file.name
            client.Configuration.set_default(configuration)
            self._api_client = client
        finally:
            pass

        return self._api_client

    def get_api_client(self) -> Any:
        return self._load_client()

    async def validate(self) -> ValidationResult:
        try:
            api = self._load_client()
        except ValueError as exc:
            return ValidationResult(
                status=ConnectionStatus.ERROR,
                cluster_name=self._cluster_name,
                region=self._region,
                error_message=str(exc),
                error_code="eks_config_failed",
            )
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            logger.warning("eks_client_failed", error_type=type(exc).__name__)
            if "ExpiredToken" in msg or "expired" in msg.lower():
                return ValidationResult(
                    status=ConnectionStatus.EXPIRED,
                    cluster_name=self._cluster_name,
                    region=self._region,
                    error_message="AWS credentials expired",
                    error_code="credential_expired",
                )
            if "Unauthorized" in msg or "401" in msg:
                return ValidationResult(
                    status=ConnectionStatus.AUTH_FAILED,
                    cluster_name=self._cluster_name,
                    region=self._region,
                    error_message="Authentication failed for EKS cluster",
                    error_code="auth_failed",
                )
            return ValidationResult(
                status=ConnectionStatus.UNREACHABLE,
                cluster_name=self._cluster_name,
                region=self._region,
                error_message="Unable to reach EKS cluster",
                error_code="unreachable",
            )

        result = validate_api_client(
            api,
            cluster_name=self._cluster_name,
            cluster_endpoint=self._cluster_endpoint,
            region=self._region,
        )
        if self._kubernetes_version and not result.kubernetes_version:
            result.kubernetes_version = f"v{self._kubernetes_version.lstrip('v')}"
        return result
