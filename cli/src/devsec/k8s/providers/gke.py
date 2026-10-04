"""Google GKE Kubernetes provider (not yet implemented)."""

from __future__ import annotations

from typing import Any

from devsec.api.client import ApiClient
from devsec.k8s.providers.base import KubernetesProvider
from devsec.utils.errors import UsageError


class GkeProvider(KubernetesProvider):
    provider_type = "gke"
    display_name = "Google GKE"

    def validate_prerequisites(self, client: ApiClient) -> dict[str, Any]:
        raise UsageError(
            "GKE integration is not yet available.",
            hint="Connect GKE clusters via kubeconfig: devsec k8s config --kubeconfig <path>",
        )

    def connect(self, client: ApiClient, name: str, **kwargs: Any) -> dict[str, Any]:
        raise UsageError(
            "GKE integration is not yet available.",
            hint="Connect GKE clusters via kubeconfig: devsec k8s config --kubeconfig <path>",
        )
