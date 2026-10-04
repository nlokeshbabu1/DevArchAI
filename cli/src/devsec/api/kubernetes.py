"""Kubernetes API client helpers for the CLI."""

from __future__ import annotations

from typing import Any

from devsec.api.client import ApiClient


def list_connections(client: ApiClient) -> list[dict[str, Any]]:
    return client.get_json("/kubernetes/connections")


def get_connection(client: ApiClient, connection_id: str) -> dict[str, Any]:
    return client.get_json(f"/kubernetes/connections/{connection_id}")


def disconnect_cluster(client: ApiClient, connection_id: str) -> dict[str, Any]:
    return client.delete(f"/kubernetes/connections/{connection_id}").json()


def test_kubeconfig(
    client: ApiClient,
    name: str,
    kubeconfig: str,
    context_name: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": name, "kubeconfig": kubeconfig}
    if context_name:
        payload["context_name"] = context_name
    return client.post_json("/kubernetes/test", payload)


def connect_cluster(
    client: ApiClient,
    name: str,
    kubeconfig: str,
    context_name: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": name, "kubeconfig": kubeconfig}
    if context_name:
        payload["context_name"] = context_name
    return client.post_json("/kubernetes/connect", payload)


def eks_aws_available(client: ApiClient) -> dict[str, Any]:
    return client.get_json("/kubernetes/eks/aws-available")


def list_eks_clusters(client: ApiClient, region: str) -> list[dict[str, Any]]:
    return client.get_json("/kubernetes/eks/clusters", params={"region": region})


def connect_eks(
    client: ApiClient,
    cluster_name: str,
    region: str,
    name: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"cluster_name": cluster_name, "region": region}
    if name:
        payload["name"] = name
    return client.post_json("/kubernetes/eks/connect", payload)


def get_overview(client: ApiClient, connection_id: str) -> dict[str, Any]:
    return client.get_json(f"/kubernetes/connections/{connection_id}/overview")


def refresh_cluster(client: ApiClient, connection_id: str) -> dict[str, Any]:
    return client.post_json(f"/kubernetes/connections/{connection_id}/refresh")


def get_nodes(client: ApiClient, connection_id: str) -> dict[str, Any]:
    return client.get_json(f"/kubernetes/connections/{connection_id}/nodes")


def get_pods(client: ApiClient, connection_id: str, namespace: str | None = None) -> dict[str, Any]:
    params = {"namespace": namespace} if namespace else None
    return client.get_json(f"/kubernetes/connections/{connection_id}/pods", params=params)


def get_deployments(client: ApiClient, connection_id: str) -> dict[str, Any]:
    return client.get_json(f"/kubernetes/connections/{connection_id}/deployments")


def get_services(client: ApiClient, connection_id: str) -> dict[str, Any]:
    return client.get_json(f"/kubernetes/connections/{connection_id}/services")


def get_ingresses(client: ApiClient, connection_id: str) -> dict[str, Any]:
    return client.get_json(f"/kubernetes/connections/{connection_id}/ingresses")


def get_events(client: ApiClient, connection_id: str) -> dict[str, Any]:
    return client.get_json(f"/kubernetes/connections/{connection_id}/events")


def get_health_score(client: ApiClient, connection_id: str) -> dict[str, Any]:
    return client.get_json(f"/kubernetes/connections/{connection_id}/health-score")


def get_security_findings(client: ApiClient, connection_id: str) -> dict[str, Any]:
    return client.get_json(f"/kubernetes/connections/{connection_id}/security-findings")


def get_latest_ai(client: ApiClient, connection_id: str) -> dict[str, Any] | None:
    return client.get_json(f"/kubernetes/connections/{connection_id}/ai-analysis/latest")


def get_ai_job(client: ApiClient, connection_id: str, job_id: str) -> dict[str, Any]:
    return client.get_json(f"/kubernetes/connections/{connection_id}/ai-analysis/{job_id}")


def validate_connection(client: ApiClient, connection_id: str) -> dict[str, Any]:
    return client.post_json(f"/kubernetes/connections/{connection_id}/validate")


def security_scan(client: ApiClient, connection_id: str) -> dict[str, Any]:
    return client.post_json(f"/kubernetes/connections/{connection_id}/security-scan")


def version_advisor(
    client: ApiClient,
    connection_id: str,
    target_version: str | None = None,
) -> dict[str, Any]:
    params = {"target_version": target_version} if target_version else None
    return client.get_json(f"/kubernetes/connections/{connection_id}/version-advisor", params=params)


def start_upgrade_analysis(
    client: ApiClient,
    connection_id: str,
    target_version: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if target_version:
        payload["target_version"] = target_version
    return client.post_json(f"/kubernetes/connections/{connection_id}/upgrade-analysis", payload)


def get_upgrade_job(client: ApiClient, connection_id: str, job_id: str) -> dict[str, Any]:
    return client.get_json(f"/kubernetes/connections/{connection_id}/upgrade-analysis/{job_id}")


def start_ai(
    client: ApiClient,
    connection_id: str,
    question: str | None = None,
    analysis_type: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if question:
        payload["question"] = question
    if analysis_type:
        payload["analysis_type"] = analysis_type
    return client.post_json(f"/kubernetes/connections/{connection_id}/ai-analysis", payload)
