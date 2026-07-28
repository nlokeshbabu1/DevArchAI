"""EC2 scanner — instances, volumes, elastic IPs, security groups."""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Any

from app.cloud.base import BaseCloudScanner, CloudCostData, CloudFindingData, CloudResourceData

logger = logging.getLogger(__name__)


class EC2Scanner(BaseCloudScanner):
    service_name = "ec2"

    async def scan(self, session: Any, regions: list[str]) -> list[CloudResourceData]:
        resources: list[CloudResourceData] = []
        for region in regions:
            region_resources = 0
            try:
                ec2 = session.client("ec2", region_name=region)

                # DescribeInstances
                resp = await asyncio.to_thread(ec2.describe_instances)
                instance_count = 0
                for reservation in resp.get("Reservations", []):
                    for inst in reservation.get("Instances", []):
                        instance_count += 1
                        name = next(
                            (t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"),
                            inst.get("InstanceId", ""),
                        )
                        resources.append(CloudResourceData(
                            provider="aws", service="ec2",
                            resource_id=inst["InstanceId"], resource_name=name,
                            resource_type="instance", region=region,
                            status=inst["State"]["Name"],
                            configuration={
                                "instance_type": inst.get("InstanceType"),
                                "platform": inst.get("Platform", "linux"),
                                "private_ip": inst.get("PrivateIpAddress"),
                                "public_ip": inst.get("PublicIpAddress"),
                                "vpc_id": inst.get("VpcId"),
                                "subnet_id": inst.get("SubnetId"),
                                "iam_instance_profile": inst.get("IamInstanceProfile", {}).get("Arn"),
                                "monitoring": inst.get("Monitoring", {}).get("State"),
                            },
                            tags={t["Key"]: t["Value"] for t in inst.get("Tags", [])},
                            created_at=inst.get("LaunchTime"),
                        ))
                logger.info("EC2 DescribeInstances: service=ec2 region=%s api=DescribeInstances found=%d", region, instance_count)

                # DescribeVolumes
                vols = await asyncio.to_thread(ec2.describe_volumes)
                vol_count = 0
                for vol in vols.get("Volumes", []):
                    vol_count += 1
                    resources.append(CloudResourceData(
                        provider="aws", service="ec2",
                        resource_id=vol["VolumeId"], resource_name=vol["VolumeId"],
                        resource_type="volume", region=region,
                        status=vol["State"],
                        configuration={
                            "size_gb": vol.get("Size"),
                            "volume_type": vol.get("VolumeType"),
                            "encrypted": vol.get("Encrypted"),
                            "availability_zone": vol.get("AvailabilityZone"),
                        },
                        created_at=vol.get("CreateTime"),
                    ))
                logger.info("EC2 DescribeVolumes: service=ec2 region=%s api=DescribeVolumes found=%d", region, vol_count)

                # DescribeAddresses
                eips = await asyncio.to_thread(ec2.describe_addresses)
                eip_count = 0
                for eip in eips.get("Addresses", []):
                    eip_count += 1
                    resources.append(CloudResourceData(
                        provider="aws", service="ec2",
                        resource_id=eip["AllocationId"],
                        resource_name=eip.get("PublicIp", ""),
                        resource_type="elastic_ip", region=region,
                        status="associated" if eip.get("InstanceId") else "unassociated",
                        configuration={
                            "allocation_id": eip.get("AllocationId"),
                            "instance_id": eip.get("InstanceId"),
                            "private_ip": eip.get("PrivateIpAddress"),
                        },
                    ))
                logger.info("EC2 DescribeAddresses: service=ec2 region=%s api=DescribeAddresses found=%d", region, eip_count)

                # DescribeSecurityGroups
                sgs = await asyncio.to_thread(ec2.describe_security_groups)
                sg_count = 0
                for sg in sgs.get("SecurityGroups", []):
                    sg_count += 1
                    resources.append(CloudResourceData(
                        provider="aws", service="ec2",
                        resource_id=sg["GroupId"], resource_name=sg["GroupName"],
                        resource_type="security_group", region=region,
                        status="active",
                        configuration={
                            "vpc_id": sg.get("VpcId"),
                            "inbound_rules": sg.get("IpPermissions", []),
                            "outbound_rules": sg.get("IpPermissionsEgress", []),
                        },
                        tags={t["Key"]: t["Value"] for t in sg.get("Tags", [])},
                    ))
                logger.info("EC2 DescribeSecurityGroups: service=ec2 region=%s api=DescribeSecurityGroups found=%d", region, sg_count)

                region_resources = instance_count + vol_count + eip_count + sg_count
            except Exception:
                tb = traceback.format_exc()
                logger.warning("EC2 scan failed for region %s\n%s", region, tb)
            logger.info("EC2 region_summary: service=ec2 region=%s total_resources=%d", region, region_resources)
        return resources

    async def check_security(self, session: Any, resources: list[CloudResourceData]) -> list[CloudFindingData]:
        findings: list[CloudFindingData] = []
        for r in resources:
            if r.resource_type == "security_group":
                for rule in r.configuration.get("inbound_rules", []):
                    for ip_range in rule.get("IpRanges", []):
                        if ip_range.get("CidrIp") == "0.0.0.0/0":
                            port = rule.get("FromPort", "*")
                            findings.append(CloudFindingData(
                                provider="aws", service="ec2",
                                category="security", severity="high",
                                title=f"Security group {r.resource_id} allows unrestricted access on port {port}",
                                description=(
                                    f"Security group {r.resource_id} ({r.resource_name}) has an inbound rule "
                                    f"allowing 0.0.0.0/0 on port {port}."
                                ),
                                resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                                rule_id="ec2-open-sg",
                                compliance_frameworks=["aws-cis", "pci-dss"],
                                remediation=f"Restrict the inbound rule to specific IP ranges instead of 0.0.0.0/0 on port {port}.",
                                evidence={"port": port, "cidr": "0.0.0.0/0", "sg_id": r.resource_id},
                            ))
            elif r.resource_type == "volume" and not r.configuration.get("encrypted"):
                findings.append(CloudFindingData(
                    provider="aws", service="ec2",
                    category="security", severity="medium",
                    title=f"EBS volume {r.resource_id} is not encrypted",
                    description=f"EBS volume {r.resource_id} in {r.region} is not encrypted. Data at rest is unprotected.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="ec2-unencrypted-volume",
                    compliance_frameworks=["aws-cis", "pci-dss", "soc2"],
                    remediation="Create an encrypted copy of the volume and migrate data.",
                ))
            elif r.resource_type == "elastic_ip" and r.status == "unassociated":
                findings.append(CloudFindingData(
                    provider="aws", service="ec2",
                    category="cost", severity="low",
                    title=f"Unassociated Elastic IP {r.resource_id}",
                    description=f"Elastic IP {r.resource_id} in {r.region} is not associated with any instance.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    rule_id="ec2-unused-eip",
                    remediation="Release the unassociated Elastic IP address.",
                ))
        return findings

    async def check_cost(self, session: Any, resources: list[CloudResourceData]) -> list[CloudCostData]:
        cost_recs: list[CloudCostData] = []
        for r in resources:
            if r.resource_type == "volume" and r.status == "available":
                size = r.configuration.get("size_gb", 0)
                cost_recs.append(CloudCostData(
                    provider="aws", service="ec2",
                    title=f"Unused EBS volume {r.resource_id}",
                    description=f"Volume {r.resource_id} ({size}GB, {r.configuration.get('volume_type', 'gp2')}) is not attached.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    monthly_savings=round(size * 0.08, 2),
                    current_cost=round(size * 0.08, 2),
                    priority="medium", category="unused_volume",
                    recommendation_type="delete",
                    estimated_impact=f"Save ~${round(size * 0.08, 2)}/month",
                ))
            elif r.resource_type == "instance" and r.status == "stopped":
                cost_recs.append(CloudCostData(
                    provider="aws", service="ec2",
                    title=f"Stopped EC2 instance {r.resource_id}",
                    description=f"Instance {r.resource_id} ({r.configuration.get('instance_type')}) is stopped.",
                    resource_id=r.resource_id, resource_type=r.resource_type, region=r.region,
                    monthly_savings=5.0, current_cost=5.0,
                    priority="low", category="stopped_instance",
                    recommendation_type="terminate",
                    estimated_impact="Save ~$5/month (EBS storage costs)",
                ))
        return cost_recs
