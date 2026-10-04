"""Google GKE connector stub — UI shows Coming Soon."""

from __future__ import annotations

from typing import Any

from app.kubernetes.connectors.base import ClusterConnector
from app.kubernetes.types import ConnectionStatus, ValidationResult


class GkeConnector(ClusterConnector):
    """Placeholder for future GKE support."""

    @property
    def provider_label(self) -> str:
        return "Google GKE"

    def get_api_client(self) -> Any:
        raise NotImplementedError("GKE integration is not yet available")

    async def validate(self) -> ValidationResult:
        return ValidationResult(
            status=ConnectionStatus.ERROR,
            error_message="GKE integration is coming soon",
            error_code="not_implemented",
        )
