"""Amazon EKS Kubernetes provider."""

from __future__ import annotations

from typing import Any

from devsec.api.client import ApiClient
from devsec.api.kubernetes import connect_eks, eks_aws_available, list_eks_clusters
from devsec.k8s.providers.base import KubernetesProvider
from devsec.utils.errors import UsageError


class EksProvider(KubernetesProvider):
    provider_type = "eks"
    display_name = "Amazon EKS"

    def __init__(
        self,
        region: str = "us-east-1",
        cluster_name: str | None = None,
    ) -> None:
        self._region = region
        self._cluster_name = cluster_name

    def validate_prerequisites(self, client: ApiClient) -> dict[str, Any]:
        aws = eks_aws_available(client)
        if not aws.get("available"):
            raise UsageError(
                aws.get("message") or "No active AWS connection found",
                hint="Connect AWS first: use the DevArchAI Web UI Integrations tab",
            )
        clusters = list_eks_clusters(client, self._region)
        return {
            "checks": {
                "aws_connection_found": True,
                "aws_account_validated": bool(aws.get("account_id")),
                "region_validated": bool(self._region),
                "eks_clusters_discovered": len(clusters) > 0,
            },
            "aws": aws,
            "clusters": clusters,
            "region": self._region,
        }

    def connect(self, client: ApiClient, name: str, **kwargs: Any) -> dict[str, Any]:
        prereq = self.validate_prerequisites(client)
        clusters = prereq["clusters"]
        cluster_name = self._cluster_name or kwargs.get("cluster_name")
        if not cluster_name:
            raise UsageError(
                "EKS cluster name required",
                hint="Use --cluster-name or select from: devsec k8s connect --type eks --region <region>",
            )
        match = next((c for c in clusters if c.get("name") == cluster_name), None)
        if not match:
            available = ", ".join(c.get("name", "?") for c in clusters[:10])
            raise UsageError(
                f"EKS cluster '{cluster_name}' not found in {self._region}",
                hint=f"Available clusters: {available or 'none'}",
            )
        display_name = name or cluster_name
        return connect_eks(
            client,
            cluster_name=cluster_name,
            region=self._region,
            name=display_name,
        )
