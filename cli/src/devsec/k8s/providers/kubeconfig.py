"""Kubeconfig-based Kubernetes provider (local / on-premises)."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from devsec.api.client import ApiClient
from devsec.api.kubernetes import connect_cluster, test_kubeconfig
from devsec.k8s.providers.base import KubernetesProvider
from devsec.utils.errors import UsageError


def _read_kubeconfig(path: str) -> str:
    expanded = Path(path).expanduser().resolve()
    if not expanded.is_file():
        raise UsageError(f"Kubeconfig not found: {path}")
    text = expanded.read_text(encoding="utf-8")
    if "clusters:" not in text or "contexts:" not in text:
        raise UsageError("Invalid kubeconfig: missing clusters or contexts sections")
    return text


def _encode_kubeconfig(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


class KubeconfigProvider(KubernetesProvider):
    provider_type = "kubeconfig"
    display_name = "On-Premises / Kubeconfig"

    def __init__(self, kubeconfig_path: str, context_name: str | None = None) -> None:
        self._kubeconfig_path = kubeconfig_path
        self._context_name = context_name
        self._kubeconfig_text: str | None = None

    def _load(self) -> str:
        if self._kubeconfig_text is None:
            self._kubeconfig_text = _read_kubeconfig(self._kubeconfig_path)
        return self._kubeconfig_text

    def validate_prerequisites(self, client: ApiClient) -> dict[str, Any]:
        text = self._load()
        encoded = _encode_kubeconfig(text)
        result = test_kubeconfig(
            client,
            name="validation",
            kubeconfig=encoded,
            context_name=self._context_name,
        )
        checks = {
            "kubeconfig_detected": True,
            "context_validated": bool(self._context_name or "current-context" in text),
            "api_reachable": result.get("ok", False),
            "authentication": result.get("status") not in ("auth_failed", "error"),
            "permissions_validated": result.get("ok", False),
            "cluster_discovered": bool(result.get("cluster_name")),
        }
        return {
            "checks": checks,
            "test_result": result,
            "cluster_name": result.get("cluster_name"),
            "kubernetes_version": result.get("kubernetes_version"),
            "cluster_endpoint": result.get("cluster_endpoint"),
        }

    def test(self, client: ApiClient, **kwargs: Any) -> dict[str, Any]:
        text = self._load()
        return test_kubeconfig(
            client,
            name=kwargs.get("name", "test"),
            kubeconfig=_encode_kubeconfig(text),
            context_name=self._context_name,
        )

    def connect(self, client: ApiClient, name: str, **kwargs: Any) -> dict[str, Any]:
        text = self._load()
        test_result = self.test(client, name=name)
        if not test_result.get("ok"):
            raise UsageError(
                test_result.get("message") or "Kubeconfig validation failed",
                hint="Run: devsec k8s doctor --kubeconfig <path>",
            )
        display_name = name or test_result.get("cluster_name") or Path(self._kubeconfig_path).stem
        return connect_cluster(
            client,
            name=display_name,
            kubeconfig=_encode_kubeconfig(text),
            context_name=self._context_name,
        )
