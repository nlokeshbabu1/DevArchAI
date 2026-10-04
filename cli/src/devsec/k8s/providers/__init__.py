"""Kubernetes provider factory."""

from __future__ import annotations

from devsec.k8s.providers.aks import AksProvider
from devsec.k8s.providers.base import KubernetesProvider
from devsec.k8s.providers.eks import EksProvider
from devsec.k8s.providers.gke import GkeProvider
from devsec.k8s.providers.kubeconfig import KubeconfigProvider
from devsec.utils.errors import UsageError

_PROVIDER_TYPES = {
    "kubeconfig": "kubeconfig",
    "generic": "kubeconfig",
    "local": "kubeconfig",
    "on-prem": "kubeconfig",
    "onprem": "kubeconfig",
    "eks": "eks",
    "aks": "aks",
    "gke": "gke",
}


def get_provider(
    provider_type: str,
    *,
    kubeconfig: str | None = None,
    context: str | None = None,
    region: str = "us-east-1",
    cluster_name: str | None = None,
) -> KubernetesProvider:
    """Resolve a provider instance from a type string."""
    normalized = _PROVIDER_TYPES.get(provider_type.lower().strip())
    if not normalized:
        raise UsageError(
            f"Unknown provider type: {provider_type}",
            hint="Supported types: kubeconfig, eks, aks, gke",
        )
    if normalized == "kubeconfig":
        if not kubeconfig:
            raise UsageError("--kubeconfig is required for kubeconfig provider")
        return KubeconfigProvider(kubeconfig, context_name=context)
    if normalized == "eks":
        return EksProvider(region=region, cluster_name=cluster_name)
    if normalized == "aks":
        return AksProvider()
    if normalized == "gke":
        return GkeProvider()
    raise UsageError(f"Unsupported provider: {provider_type}")
