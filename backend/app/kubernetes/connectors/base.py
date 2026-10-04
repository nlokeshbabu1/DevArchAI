"""Base cluster connector abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.kubernetes.types import ValidationResult


class ClusterConnector(ABC):
    """Provider-specific Kubernetes API access."""

    @abstractmethod
    async def validate(self) -> ValidationResult:
        """Validate connectivity, TLS, auth, and read-only RBAC."""

    @abstractmethod
    def get_api_client(self) -> Any:
        """Return a configured kubernetes client (CoreV1Api, etc.)."""

    @property
    @abstractmethod
    def provider_label(self) -> str:
        """Human-readable provider name."""
