"""Azure AKS Kubernetes provider (not yet implemented)."""

from __future__ import annotations

from typing import Any

from devsec.api.client import ApiClient
from devsec.k8s.providers.base import KubernetesProvider
from devsec.utils.errors import UsageError


class AksProvider(KubernetesProvider):
    provider_type = "aks"
    display_name = "Azure AKS"

    def validate_prerequisites(self, client: ApiClient) -> dict[str, Any]:
        raise UsageError(
            "AKS integration is not yet available.",
            hint="Connect AKS clusters via kubeconfig: devsec k8s config --kubeconfig <path>",
        )

    def connect(self, client: ApiClient, name: str, **kwargs: Any) -> dict[str, Any]:
        raise UsageError(
            "AKS integration is not yet available.",
            hint="Connect AKS clusters via kubeconfig: devsec k8s config --kubeconfig <path>",
        )
