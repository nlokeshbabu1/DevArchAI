"""Factory for provider-specific cluster connectors."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.cloud.aws.sts import assume_customer_role
from app.core.encryption import get_encryption_service
from app.kubernetes.connectors.base import ClusterConnector
from app.kubernetes.connectors.eks import EksConnector
from app.kubernetes.connectors.generic import GenericConnector
from app.kubernetes.credentials import get_kubeconfig_text
from app.models.cloud import CloudConnection
from app.models.kubernetes import KubernetesConnection


async def build_connector(
    connection: KubernetesConnection,
    db: AsyncSession,
    *,
    kubeconfig_override: str | None = None,
) -> ClusterConnector:
    """Build the appropriate connector for a stored connection."""
    if connection.kind == "eks":
        from sqlalchemy import select

        result = await db.execute(
            select(CloudConnection).where(
                CloudConnection.user_id == connection.user_id,
                CloudConnection.provider == "aws",
                CloudConnection.status == "active",
            )
        )
        aws_conn = result.scalars().first()
        if not aws_conn:
            raise ValueError("Active AWS connection required for EKS cluster access")

        encryption = get_encryption_service()
        external_id = encryption.decrypt(aws_conn.external_id_encrypted or "")
        role_name = aws_conn.role_arn.split("/")[-1]
        session = assume_customer_role(
            customer_account_id=aws_conn.account_id,
            customer_role_name=role_name,
            external_id=external_id,
            session_name="devarchai-k8s",
        )
        return EksConnector(
            cluster_name=connection.eks_cluster_name or connection.name,
            region=connection.aws_region or "us-east-1",
            aws_session=session,
            cluster_endpoint=connection.cluster_endpoint,
        )

    kubeconfig = kubeconfig_override or get_kubeconfig_text(connection)
    if not kubeconfig:
        raise ValueError("No kubeconfig available for this connection")

    return GenericConnector(kubeconfig, context_name=connection.context_name)
