"""ELB scanner — load balancers, target groups, listeners."""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any

from app.cloud.base import BaseCloudScanner, CloudFindingData, CloudResourceData

logger = logging.getLogger(__name__)


class ELBScanner(BaseCloudScanner):
    service_name = "elb"

    async def scan(self, session: Any, regions: list[str]) -> list[CloudResourceData]:
        resources: list[CloudResourceData] = []
        for region in regions:
            region_resources = 0
            try:
                elbv2 = session.client("elbv2", region_name=region)

                # DescribeLoadBalancers
                lbs_resp = await asyncio.to_thread(elbv2.describe_load_balancers)
                lb_count = 0
                for lb in lbs_resp.get("LoadBalancers", []):
                    lb_count += 1
                    lb_name = lb.get("LoadBalancerName", lb.get("DNSName", ""))
                    resources.append(CloudResourceData(
                        provider="aws", service="elb",
                        resource_id=lb["LoadBalancerArn"], resource_name=lb_name,
                        resource_type="load_balancer", region=region,
                        status=lb.get("State", {}).get("Code", "unknown"),
                        configuration={
                            "type": lb.get("Type"),
                            "scheme": lb.get("Scheme"),
                            "dns_name": lb.get("DNSName"),
                            "vpc_id": lb.get("VpcId"),
                            "security_groups": lb.get("SecurityGroups", []),
                            "subnets": lb.get("AvailabilityZones", []),
                        },
                        tags={}, created_at=lb.get("CreatedTime"),
                    ))
                logger.info("ELB DescribeLoadBalancers: service=elb region=%s api=DescribeLoadBalancers found=%d", region, lb_count)

                # DescribeTargetGroups
                tg_resp = await asyncio.to_thread(elbv2.describe_target_groups)
                tg_count = 0
                for tg in tg_resp.get("TargetGroups", []):
                    tg_count += 1
                    resources.append(CloudResourceData(
                        provider="aws", service="elb",
                        resource_id=tg["TargetGroupArn"], resource_name=tg["TargetGroupName"],
                        resource_type="target_group", region=region, status="active",
                        configuration={
                            "protocol": tg.get("Protocol"),
                            "port": tg.get("Port"),
                            "vpc_id": tg.get("VpcId"),
                            "target_type": tg.get("TargetType"),
                            "health_check_path": tg.get("HealthCheckPath"),
                        },
                    ))
                logger.info("ELB DescribeTargetGroups: service=elb region=%s api=DescribeTargetGroups found=%d", region, tg_count)

                # Classic ELBs
                try:
                    elb_classic = session.client("elasticloadbalancing", region_name=region)
                    classic_resp = await asyncio.to_thread(elb_classic.describe_load_balancers)
                    classic_count = 0
                    for lb in classic_resp.get("LoadBalancerDescriptions", []):
                        classic_count += 1
                        resources.append(CloudResourceData(
                            provider="aws", service="elb",
                            resource_id=lb["LoadBalancerName"],
                            resource_name=lb["LoadBalancerName"],
                            resource_type="classic_load_balancer", region=region, status="active",
                            configuration={
                                "dns_name": lb.get("DNSName"),
                                "scheme": lb.get("Scheme"),
                                "vpc_id": lb.get("VPCId"),
                                "listeners": [
                            {"protocol": lst.get("Protocol"), "port": lst.get("LoadBalancerPort")}
                            for lst in lb.get("ListenerDescriptions", [])
                                ],
                            },
                            created_at=lb.get("CreatedTime"),
                        ))
                    logger.info("ELB ClassicELBs: service=elb region=%s api=DescribeLoadBalancers(classic) found=%d", region, classic_count)
                except Exception:
                    pass

                region_resources = lb_count + tg_count
            except Exception:
                tb = traceback.format_exc()
                logger.warning("ELB scan failed for region %s\n%s", region, tb)
            logger.info("ELB region_summary: service=elb region=%s total_resources=%d", region, region_resources)
        return resources

    async def check_security(self, session: Any, resources: list[CloudResourceData]) -> list[CloudFindingData]:
        findings: list[CloudFindingData] = []
        for r in resources:
            if r.resource_type == "load_balancer" and r.configuration.get("scheme") == "internet-facing":
                if not r.configuration.get("security_groups"):
                    findings.append(CloudFindingData(
                        provider="aws", service="elb", category="security", severity="high",
                        title=f"Internet-facing ALB {r.resource_name} has no security groups",
                        description=f"ALB {r.resource_name} in {r.region} is internet-facing but has no security groups attached.",
                        resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                        rule_id="elb-no-sg", compliance_frameworks=["aws-cis"],
                        remediation="Attach security groups with appropriate ingress/egress rules.",
                    ))
            elif r.resource_type == "classic_load_balancer":
                for listener in r.configuration.get("listeners", []):
                    if listener.get("protocol") == "HTTP":
                        findings.append(CloudFindingData(
                            provider="aws", service="elb", category="security", severity="medium",
                            title=f"Classic ELB {r.resource_name} uses HTTP",
                            description=f"Classic ELB {r.resource_name} has an HTTP listener on port {listener.get('port')}.",
                            resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                            rule_id="elb-http-listener", compliance_frameworks=["aws-cis", "pci-dss"],
                            remediation="Use HTTPS with a valid SSL certificate instead of HTTP.",
                        ))
        return findings
