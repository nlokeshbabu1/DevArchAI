"""Kubernetes API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class KubernetesConnectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    kubeconfig: str = Field(..., min_length=1, description="Base64-encoded kubeconfig YAML")
    context_name: str | None = Field(default=None, max_length=200)


class EksConnectRequest(BaseModel):
    cluster_name: str = Field(..., min_length=1, max_length=200)
    region: str = Field(..., min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=200)


class PermissionInfo(BaseModel):
    resource: str
    granted: bool
    error: str | None = None


class KubernetesInfo(BaseModel):
    id: str
    name: str
    provider: str
    kind: str
    context_name: str | None = None
    cluster_name: str | None = None
    cluster_endpoint: str | None = None
    aws_account_id: str | None = None
    aws_region: str | None = None
    eks_cluster_name: str | None = None
    kubernetes_version: str | None = None
    health_status: str | None = None
    status: str
    is_active: bool
    node_count: int | None = None
    pod_count: int | None = None
    service_count: int | None = None
    namespace_count: int | None = None
    deployment_count: int | None = None
    ingress_count: int | None = None
    last_verified_at: str | None = None
    error_message: str | None = None
    permissions: list[PermissionInfo] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ClusterAIJobInfo(BaseModel):
    id: str
    connection_id: str
    status: str
    analysis_type: str
    result: dict | None = None
    error_message: str | None = None
    finding_count: int | None = None
    recommendation_count: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str | None = None


class UpgradeAnalysisRequest(BaseModel):
    target_version: str | None = Field(default=None, description="Target K8s version e.g. v1.34")


class AIAnalysisRequest(BaseModel):
    question: str | None = Field(default=None, max_length=2000)
    analysis_type: str | None = Field(default="copilot", description="copilot|troubleshoot|cluster")
