"""Generic kubeconfig-based cluster connector."""

from __future__ import annotations

import tempfile
from typing import Any

import structlog
import yaml

from app.kubernetes.connectors.base import ClusterConnector
from app.kubernetes.validator import validate_api_client
from app.kubernetes.types import ConnectionStatus, ValidationResult

logger = structlog.get_logger(__name__)


class GenericConnector(ClusterConnector):
    """Connect using a stored or supplied kubeconfig."""

    def __init__(self, kubeconfig_text: str, context_name: str | None = None) -> None:
        self._kubeconfig_text = kubeconfig_text
        self._context_name = context_name
        self._api_client: Any = None
        self._cluster_name: str | None = None
        self._cluster_endpoint: str | None = None

    @property
    def provider_label(self) -> str:
        return "Kubernetes"

    def _load_client(self) -> Any:
        if self._api_client is not None:
            return self._api_client

        from kubernetes import client, config
        from kubernetes.config.kube_config import load_kube_config_from_dict

        try:
            kubeconfig_dict = yaml.safe_load(self._kubeconfig_text)
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid kubeconfig YAML: {exc}") from exc

        if not isinstance(kubeconfig_dict, dict):
            raise ValueError("Invalid kubeconfig: expected mapping")

        context = self._context_name
        if not context:
            context = kubeconfig_dict.get("current-context")

        load_kube_config_from_dict(kubeconfig_dict, context=context)
        self._api_client = client

        contexts = kubeconfig_dict.get("contexts") or []
        clusters = {c.get("name"): c for c in (kubeconfig_dict.get("clusters") or [])}
        for ctx in contexts:
            if ctx.get("name") == context:
                cluster_ref = (ctx.get("context") or {}).get("cluster")
                cluster = clusters.get(cluster_ref, {})
                self._cluster_name = cluster_ref or context
                self._cluster_endpoint = (cluster.get("cluster") or {}).get("server")
                break

        if not self._cluster_name:
            self._cluster_name = context or "cluster"

        return self._api_client

    def get_api_client(self) -> Any:
        return self._load_client()

    async def validate(self) -> ValidationResult:
        try:
            api = self._load_client()
        except ValueError as exc:
            return ValidationResult(
                status=ConnectionStatus.ERROR,
                error_message=str(exc),
                error_code="invalid_kubeconfig",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("kubeconfig_load_failed", error_type=type(exc).__name__)
            return ValidationResult(
                status=ConnectionStatus.ERROR,
                error_message="Failed to load kubeconfig",
                error_code="kubeconfig_load_failed",
            )

        return validate_api_client(
            api,
            cluster_name=self._cluster_name,
            cluster_endpoint=self._cluster_endpoint,
            region=None,
        )
