"""Azure AKS connector stub — UI shows Coming Soon."""

from __future__ import annotations

from typing import Any

from app.kubernetes.connectors.base import ClusterConnector
from app.kubernetes.types import ConnectionStatus, ValidationResult


class AksConnector(ClusterConnector):
    """Placeholder for future AKS support."""

    @property
    def provider_label(self) -> str:
        return "Azure AKS"

    def get_api_client(self) -> Any:
        raise NotImplementedError("AKS integration is not yet available")

    async def validate(self) -> ValidationResult:
        return ValidationResult(
            status=ConnectionStatus.ERROR,
            error_message="AKS integration is coming soon",
            error_code="not_implemented",
        )
