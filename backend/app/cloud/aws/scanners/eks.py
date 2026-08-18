"""EKS scanner — clusters, node groups, namespaces."""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any

from app.cloud.base import BaseCloudScanner, CloudFindingData, CloudResourceData

logger = logging.getLogger(__name__)


class EKSScanner(BaseCloudScanner):
    service_name = "eks"

    async def scan(self, session: Any, regions: list[str]) -> list[CloudResourceData]:
        resources: list[CloudResourceData] = []
        for region in regions:
            region_resources = 0
            try:
                eks = session.client("eks", region_name=region)
                clusters_resp = await asyncio.to_thread(eks.list_clusters)
                cluster_names = clusters_resp.get("clusters", [])
                logger.info("EKS ListClusters: service=eks region=%s api=ListClusters found=%d", region, len(cluster_names))
                for cluster_name in cluster_names:
                    desc = await asyncio.to_thread(eks.describe_cluster, name=cluster_name)
                    cluster = desc.get("cluster", {})
                    region_resources += 1
                    resources.append(CloudResourceData(
                        provider="aws", service="eks",
                        resource_id=cluster.get("arn", cluster_name),
                        resource_name=cluster_name,
                        resource_type="cluster", region=region,
                        status=cluster.get("status", "unknown"),
                        configuration={
                            "version": cluster.get("version"),
                            "endpoint": cluster.get("endpoint"),
                            "vpc_id": cluster.get("resourcesVpcConfig", {}).get("vpcId"),
                            "role_arn": cluster.get("roleArn"),
                            "logging": cluster.get("logging"),
                        },
                        tags=cluster.get("tags", {}),
                        created_at=cluster.get("createdAt"),
                    ))
                    # Node groups
                    try:
                        ng_resp = await asyncio.to_thread(
                            eks.list_nodegroups, clusterName=cluster_name
                        )
                        ng_count = 0
                        for ng_name in ng_resp.get("nodegroups", []):
                            ng_desc = await asyncio.to_thread(
                                eks.describe_nodegroup, clusterName=cluster_name, nodegroupName=ng_name
                            )
                            ng = ng_desc.get("nodegroup", {})
                            ng_count += 1
                            region_resources += 1
                            resources.append(CloudResourceData(
                                provider="aws", service="eks",
                                resource_id=ng.get("nodegroupArn", ng_name),
                                resource_name=ng_name,
                                resource_type="nodegroup", region=region,
                                status=ng.get("status", "unknown"),
                                configuration={
                                    "cluster_name": cluster_name,
                                    "instance_types": ng.get("instanceTypes"),
                                    "disk_size": ng.get("diskSize"),
                                    "ami_type": ng.get("amiType"),
                                    "scaling_config": ng.get("scalingConfig"),
                                },
                                tags=ng.get("tags", {}),
                                created_at=ng.get("createdAt"),
                            ))
                        logger.info("EKS ListNodegroups: service=eks region=%s cluster=%s api=ListNodegroups found=%d", region, cluster_name, ng_count)
                    except Exception:
                        logger.warning("Failed to list nodegroups for %s", cluster_name, exc_info=True)
            except Exception:
                tb = traceback.format_exc()
                logger.warning("EKS scan failed for region %s\n%s", region, tb)
            logger.info("EKS region_summary: service=eks region=%s total_resources=%d", region, region_resources)
        return resources

    async def check_security(self, session: Any, resources: list[CloudResourceData]) -> list[CloudFindingData]:
        findings: list[CloudFindingData] = []
        for r in resources:
            if r.resource_type == "cluster":
                logging_config = r.configuration.get("logging")
                if not logging_config or not logging_config.get("clusterLogging"):
                    findings.append(CloudFindingData(
                        provider="aws", service="eks", category="security", severity="medium",
                        title=f"EKS cluster {r.resource_name} has no control plane logging",
                        description=f"EKS cluster {r.resource_name} in {r.region} does not have control plane logging enabled.",
                        resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                        rule_id="eks-no-logging", compliance_frameworks=["aws-cis"],
                        remediation="Enable control plane logging (api, audit, authenticator, controllerManager, scheduler).",
                    ))
            elif r.resource_type == "nodegroup":
                disk = r.configuration.get("disk_size", 0)
                if disk and disk < 20:
                    findings.append(CloudFindingData(
                        provider="aws", service="eks", category="security", severity="low",
                        title=f"EKS nodegroup {r.resource_name} has small disk size ({disk}GB)",
                        description=f"Nodegroup {r.resource_name} has a disk size of only {disk}GB.",
                        resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                        rule_id="eks-small-disk",
                        remediation="Increase disk size for production node groups.",
                    ))
        return findings
