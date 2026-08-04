"""VPC scanner — VPCs, subnets, route tables, NACLs, internet gateways."""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any

from app.cloud.base import BaseCloudScanner, CloudFindingData, CloudResourceData

logger = logging.getLogger(__name__)


class VPCScanner(BaseCloudScanner):
    service_name = "vpc"

    async def scan(self, session: Any, regions: list[str]) -> list[CloudResourceData]:
        resources: list[CloudResourceData] = []
        for region in regions:
            region_resources = 0
            try:
                ec2 = session.client("ec2", region_name=region)

                # DescribeVpcs
                vpcs = await asyncio.to_thread(ec2.describe_vpcs)
                vpc_count = 0
                for vpc in vpcs.get("Vpcs", []):
                    vpc_count += 1
                    name = next(
                        (t["Value"] for t in vpc.get("Tags", []) if t["Key"] == "Name"),
                        vpc["VpcId"],
                    )
                    resources.append(CloudResourceData(
                        provider="aws", service="vpc",
                        resource_id=vpc["VpcId"], resource_name=name,
                        resource_type="vpc", region=region, status="active",
                        configuration={
                            "cidr_block": vpc.get("CidrBlock"),
                            "is_default": vpc.get("IsDefault", False),
                            "dhcp_options_id": vpc.get("DhcpOptionsId"),
                        },
                        tags={t["Key"]: t["Value"] for t in vpc.get("Tags", [])},
                    ))
                logger.info("VPC DescribeVpcs: service=vpc region=%s api=DescribeVpcs found=%d", region, vpc_count)

                # DescribeSubnets
                subnets = await asyncio.to_thread(ec2.describe_subnets)
                subnet_count = 0
                for sub in subnets.get("Subnets", []):
                    subnet_count += 1
                    name = next(
                        (t["Value"] for t in sub.get("Tags", []) if t["Key"] == "Name"),
                        sub["SubnetId"],
                    )
                    resources.append(CloudResourceData(
                        provider="aws", service="vpc",
                        resource_id=sub["SubnetId"], resource_name=name,
                        resource_type="subnet", region=region, status="active",
                        configuration={
                            "vpc_id": sub.get("VpcId"),
                            "cidr_block": sub.get("CidrBlock"),
                            "availability_zone": sub.get("AvailabilityZone"),
                            "public": sub.get("MapPublicIpOnLaunch", False),
                        },
                        tags={t["Key"]: t["Value"] for t in sub.get("Tags", [])},
                    ))
                logger.info("VPC DescribeSubnets: service=vpc region=%s api=DescribeSubnets found=%d", region, subnet_count)

                # DescribeRouteTables
                rtbs = await asyncio.to_thread(ec2.describe_route_tables)
                rtb_count = 0
                for rtb in rtbs.get("RouteTables", []):
                    rtb_count += 1
                    name = next(
                        (t["Value"] for t in rtb.get("Tags", []) if t["Key"] == "Name"),
                        rtb["RouteTableId"],
                    )
                    resources.append(CloudResourceData(
                        provider="aws", service="vpc",
                        resource_id=rtb["RouteTableId"], resource_name=name,
                        resource_type="route_table", region=region, status="active",
                        configuration={
                            "vpc_id": next(
                                (a["VpcId"] for a in rtb.get("Associations", []) if a.get("Main")),
                                None,
                            ),
                            "routes": [
                                {"dest": r.get("DestinationCidrBlock"), "gateway": r.get("GatewayId")}
                                for r in rtb.get("Routes", [])
                            ],
                        },
                        tags={t["Key"]: t["Value"] for t in rtb.get("Tags", [])},
                    ))
                logger.info("VPC DescribeRouteTables: service=vpc region=%s api=DescribeRouteTables found=%d", region, rtb_count)

                # DescribeNetworkAcls
                nacls = await asyncio.to_thread(ec2.describe_network_acls)
                nacl_count = 0
                for nacl in nacls.get("NetworkAcls", []):
                    nacl_count += 1
                    resources.append(CloudResourceData(
                        provider="aws", service="vpc",
                        resource_id=nacl["NetworkAclId"],
                        resource_name=nacl.get("NetworkAclId", ""),
                        resource_type="nacl", region=region, status="active",
                        configuration={
                            "vpc_id": nacl.get("VpcId"),
                            "entries_count": len(nacl.get("Entries", [])),
                        },
                        tags={t["Key"]: t["Value"] for t in nacl.get("Tags", [])},
                    ))
                logger.info("VPC DescribeNetworkAcls: service=vpc region=%s api=DescribeNetworkAcls found=%d", region, nacl_count)

                region_resources = vpc_count + subnet_count + rtb_count + nacl_count
            except Exception:
                tb = traceback.format_exc()
                logger.warning("VPC scan failed for region %s\n%s", region, tb)
            logger.info("VPC region_summary: service=vpc region=%s total_resources=%d", region, region_resources)
        return resources

    async def check_security(self, session: Any, resources: list[CloudResourceData]) -> list[CloudFindingData]:
        findings: list[CloudFindingData] = []
        for r in resources:
            if r.resource_type == "subnet" and r.configuration.get("public"):
                findings.append(CloudFindingData(
                    provider="aws", service="vpc", category="security", severity="info",
                    title=f"Subnet {r.resource_id} auto-assigns public IPs",
                    description=f"Subnet {r.resource_id} in {r.region} has MapPublicIpOnLaunch enabled.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="vpc-public-subnet",
                    compliance_frameworks=["aws-cis"],
                    remediation="Disable MapPublicIpOnLaunch if public IPs are not required.",
                ))
            elif r.resource_type == "vpc" and r.configuration.get("is_default"):
                findings.append(CloudFindingData(
                    provider="aws", service="vpc", category="security", severity="info",
                    title=f"Default VPC {r.resource_id} is in use",
                    description=f"Default VPC {r.resource_id} exists in {r.region}. Consider deleting it.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="vpc-default-vpc",
                    remediation="Delete the default VPC or restrict its configuration.",
                ))
        return findings
