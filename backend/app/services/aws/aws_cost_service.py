"""AWS cost optimization analysis service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog

from app.services.aws.aws_client import AWSIntegrationError, call_aws, client, enabled_regions

logger = structlog.get_logger(__name__)


class AWSCostService:
    """Detect AWS cost optimization opportunities."""

    async def analyze(self, session, default_region: str) -> list[dict]:
        regions = await enabled_regions(session, default_region)
        recommendations = []
        for region in regions:
            recommendations.extend(await self._check_ec2(session, region))
            recommendations.extend(await self._check_ebs(session, region))
            recommendations.extend(await self._check_elastic_ips(session, region))
            recommendations.extend(await self._check_nat_gateways(session, region))
            recommendations.extend(await self._check_snapshots(session, region))
            recommendations.extend(await self._check_rds(session, region))
        recommendations.extend(await self._cost_explorer_summary(session, default_region))
        return recommendations

    def _rec(self, rec_type, title, description, resource_type=None, resource_id=None, region=None, savings=0.0, metadata=None):
        return {"recommendation_type": rec_type, "title": title, "description": description, "resource_type": resource_type, "resource_id": resource_id, "region": region, "estimated_monthly_savings": savings, "metadata": metadata or {}}

    async def _check_ec2(self, session, region: str) -> list[dict]:
        ec2 = client(session, "ec2", region)
        cloudwatch = client(session, "cloudwatch", region)
        recs = []
        try:
            instances = await call_aws(ec2.describe_instances, Filters=[{"Name": "instance-state-name", "Values": ["running", "stopped"]}])
            for reservation in instances.get("Reservations", []):
                for item in reservation.get("Instances", []):
                    instance_id = item["InstanceId"]
                    state = item.get("State", {}).get("Name")
                    if state == "stopped":
                        recs.append(self._rec("idle_ec2", "Stopped EC2 instance", f"EC2 instance {instance_id} is stopped but may still incur EBS costs.", "ec2", instance_id, region, 8.0))
                        continue
                    metrics = await call_aws(
                        cloudwatch.get_metric_statistics,
                        Namespace="AWS/EC2",
                        MetricName="CPUUtilization",
                        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                        StartTime=datetime.now(timezone.utc) - timedelta(days=14),
                        EndTime=datetime.now(timezone.utc),
                        Period=86400,
                        Statistics=["Average"],
                    )
                    datapoints = metrics.get("Datapoints", [])
                    avg_cpu = sum(point["Average"] for point in datapoints) / len(datapoints) if datapoints else 0
                    if avg_cpu < 5:
                        recs.append(self._rec("low_cpu_instance", "Low CPU EC2 instance", f"EC2 instance {instance_id} averaged {avg_cpu:.1f}% CPU over 14 days.", "ec2", instance_id, region, 25.0, {"average_cpu": avg_cpu}))
        except AWSIntegrationError as exc:
            logger.warning("AWS EC2 cost analysis failed", region=region, error=str(exc))
        return recs

    async def _check_ebs(self, session, region: str) -> list[dict]:
        ec2 = client(session, "ec2", region)
        try:
            volumes = await call_aws(ec2.describe_volumes, Filters=[{"Name": "status", "Values": ["available"]}])
            return [self._rec("unattached_ebs", "Unattached EBS volume", f"EBS volume {volume['VolumeId']} is unattached.", "ebs_volume", volume["VolumeId"], region, max(float(volume.get("Size", 0)) * 0.10, 1.0)) for volume in volumes.get("Volumes", [])]
        except AWSIntegrationError as exc:
            logger.warning("AWS EBS cost analysis failed", region=region, error=str(exc))
            return []

    async def _check_elastic_ips(self, session, region: str) -> list[dict]:
        ec2 = client(session, "ec2", region)
        try:
            response = await call_aws(ec2.describe_addresses)
            return [self._rec("unused_elastic_ip", "Unused Elastic IP", f"Elastic IP {item.get('PublicIp')} is not associated.", "elastic_ip", item.get("AllocationId") or item.get("PublicIp"), region, 3.60) for item in response.get("Addresses", []) if not item.get("AssociationId")]
        except AWSIntegrationError as exc:
            logger.warning("AWS Elastic IP cost analysis failed", region=region, error=str(exc))
            return []

    async def _check_nat_gateways(self, session, region: str) -> list[dict]:
        ec2 = client(session, "ec2", region)
        try:
            response = await call_aws(ec2.describe_nat_gateways)
            return [self._rec("nat_gateway_cost", "NAT Gateway cost review", f"NAT Gateway {item['NatGatewayId']} can be a significant fixed monthly cost.", "nat_gateway", item["NatGatewayId"], region, 32.0) for item in response.get("NatGateways", []) if item.get("State") == "available"]
        except AWSIntegrationError as exc:
            logger.warning("AWS NAT Gateway cost analysis failed", region=region, error=str(exc))
            return []

    async def _check_snapshots(self, session, region: str) -> list[dict]:
        ec2 = client(session, "ec2", region)
        cutoff = datetime.now(timezone.utc) - timedelta(days=180)
        try:
            response = await call_aws(ec2.describe_snapshots, OwnerIds=["self"])
            return [self._rec("old_snapshot", "Old EBS snapshot", f"Snapshot {item['SnapshotId']} is older than 180 days.", "ebs_snapshot", item["SnapshotId"], region, max(float(item.get("VolumeSize", 0)) * 0.05, 1.0)) for item in response.get("Snapshots", []) if item.get("StartTime") and item["StartTime"] < cutoff]
        except AWSIntegrationError as exc:
            logger.warning("AWS snapshot cost analysis failed", region=region, error=str(exc))
            return []

    async def _check_rds(self, session, region: str) -> list[dict]:
        rds = client(session, "rds", region)
        cloudwatch = client(session, "cloudwatch", region)
        recs = []
        try:
            dbs = await call_aws(rds.describe_db_instances)
            for db in dbs.get("DBInstances", []):
                db_id = db["DBInstanceIdentifier"]
                metrics = await call_aws(cloudwatch.get_metric_statistics, Namespace="AWS/RDS", MetricName="CPUUtilization", Dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_id}], StartTime=datetime.now(timezone.utc) - timedelta(days=14), EndTime=datetime.now(timezone.utc), Period=86400, Statistics=["Average"])
                datapoints = metrics.get("Datapoints", [])
                avg_cpu = sum(point["Average"] for point in datapoints) / len(datapoints) if datapoints else 0
                if avg_cpu < 10:
                    recs.append(self._rec("underutilized_rds", "Underutilized RDS instance", f"RDS instance {db_id} averaged {avg_cpu:.1f}% CPU over 14 days.", "rds", db_id, region, 35.0, {"average_cpu": avg_cpu}))
        except AWSIntegrationError as exc:
            logger.warning("AWS RDS cost analysis failed", region=region, error=str(exc))
        return recs

    async def _cost_explorer_summary(self, session, region: str) -> list[dict]:
        ce = client(session, "ce", region)
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=30)
        try:
            response = await call_aws(ce.get_cost_and_usage, TimePeriod={"Start": start.isoformat(), "End": end.isoformat()}, Granularity="MONTHLY", Metrics=["UnblendedCost"], GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}])
            return [self._rec("cost_explorer_summary", "Cost Explorer baseline imported", "Cost Explorer data is available for this account.", "account", "cost-explorer", "aws-global", 0.0, {"results": response.get("ResultsByTime", [])[:1]})]
        except AWSIntegrationError as exc:
            logger.warning("AWS Cost Explorer analysis failed", error=str(exc))
            return []
