"""Kubernetes provider abstraction for the DevArchAI CLI.

Providers handle connection flows only. All cluster inspection goes through
the backend API using stored connection records.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from devsec.api.client import ApiClient


class KubernetesProvider(ABC):
    """Provider-independent interface for registering cluster connections."""

    provider_type: str
    display_name: str

    @abstractmethod
    def validate_prerequisites(self, client: ApiClient) -> dict[str, Any]:
        """Check prerequisites before connecting. Returns status dict."""

    @abstractmethod
    def connect(self, client: ApiClient, name: str, **kwargs: Any) -> dict[str, Any]:
        """Register a cluster connection with the DevArchAI backend."""

    def test(self, client: ApiClient, **kwargs: Any) -> dict[str, Any]:
        """Optional pre-connect validation. Returns test result dict."""
        return {"ok": True, "message": "No test required for this provider"}
