"""AWS inventory collection service."""

from __future__ import annotations

import structlog

from app.services.aws.aws_client import AWSIntegrationError, call_aws, client, enabled_regions

logger = structlog.get_logger(__name__)


class AWSInventoryService:
    """Collect summarized AWS resource inventory."""

    async def collect(self, session, default_region: str) -> list[dict]:
        regions = await enabled_regions(session, default_region)
        inventory: list[dict] = []
        global_region = "aws-global"
        inventory.extend(await self._collect_iam(session, default_region, global_region))

        for region in regions:
            inventory.extend(await self._collect_ec2(session, region))
            inventory.extend(await self._collect_s3(session, region))
            inventory.extend(await self._collect_rds(session, region))
            inventory.extend(await self._collect_lambda(session, region))
            inventory.extend(await self._collect_eks(session, region))
            inventory.extend(await self._collect_elb(session, region))

        return inventory

    async def _collect_ec2(self, session, region: str) -> list[dict]:
        ec2 = client(session, "ec2", region)
        resources = []
        try:
            instances = await call_aws(ec2.describe_instances)
            for reservation in instances.get("Reservations", []):
                for item in reservation.get("Instances", []):
                    name = next((tag["Value"] for tag in item.get("Tags", []) if tag.get("Key") == "Name"), item["InstanceId"])
                    resources.append({"resource_type": "ec2", "resource_id": item["InstanceId"], "name": name, "region": region, "metadata": {"state": item.get("State", {}).get("Name"), "instance_type": item.get("InstanceType"), "launch_time": str(item.get("LaunchTime"))}})

            volumes = await call_aws(ec2.describe_volumes)
            for item in volumes.get("Volumes", []):
                resources.append({"resource_type": "ebs_volume", "resource_id": item["VolumeId"], "name": item["VolumeId"], "region": region, "metadata": {"size": item.get("Size"), "state": item.get("State"), "encrypted": item.get("Encrypted"), "attachments": len(item.get("Attachments", []))}})

            addresses = await call_aws(ec2.describe_addresses)
            for item in addresses.get("Addresses", []):
                resources.append({"resource_type": "elastic_ip", "resource_id": item.get("AllocationId") or item.get("PublicIp"), "name": item.get("PublicIp"), "region": region, "metadata": {"associated": bool(item.get("AssociationId"))}})

            vpcs = await call_aws(ec2.describe_vpcs)
            for item in vpcs.get("Vpcs", []):
                resources.append({"resource_type": "vpc", "resource_id": item["VpcId"], "name": item["VpcId"], "region": region, "metadata": {"cidr": item.get("CidrBlock"), "is_default": item.get("IsDefault")}})
        except AWSIntegrationError as exc:
            logger.warning("AWS inventory EC2 collection failed", region=region, error=str(exc))
        return resources

    async def _collect_s3(self, session, region: str) -> list[dict]:
        if region != session.region_name:
            return []
        s3 = client(session, "s3", region)
        try:
            buckets = await call_aws(s3.list_buckets)
            return [{"resource_type": "s3", "resource_id": bucket["Name"], "name": bucket["Name"], "region": "aws-global", "metadata": {"creation_date": str(bucket.get("CreationDate"))}} for bucket in buckets.get("Buckets", [])]
        except AWSIntegrationError as exc:
            logger.warning("AWS inventory S3 collection failed", error=str(exc))
            return []

    async def _collect_rds(self, session, region: str) -> list[dict]:
        rds = client(session, "rds", region)
        try:
            dbs = await call_aws(rds.describe_db_instances)
            return [{"resource_type": "rds", "resource_id": item["DBInstanceIdentifier"], "name": item["DBInstanceIdentifier"], "region": region, "metadata": {"engine": item.get("Engine"), "class": item.get("DBInstanceClass"), "public": item.get("PubliclyAccessible"), "storage_encrypted": item.get("StorageEncrypted")}} for item in dbs.get("DBInstances", [])]
        except AWSIntegrationError as exc:
            logger.warning("AWS inventory RDS collection failed", region=region, error=str(exc))
            return []

    async def _collect_lambda(self, session, region: str) -> list[dict]:
        lambda_client = client(session, "lambda", region)
        try:
            response = await call_aws(lambda_client.list_functions)
            return [{"resource_type": "lambda", "resource_id": item["FunctionArn"], "name": item["FunctionName"], "region": region, "metadata": {"runtime": item.get("Runtime"), "memory": item.get("MemorySize"), "last_modified": item.get("LastModified")}} for item in response.get("Functions", [])]
        except AWSIntegrationError as exc:
            logger.warning("AWS inventory Lambda collection failed", region=region, error=str(exc))
            return []

    async def _collect_eks(self, session, region: str) -> list[dict]:
        eks = client(session, "eks", region)
        try:
            response = await call_aws(eks.list_clusters)
            return [{"resource_type": "eks", "resource_id": name, "name": name, "region": region, "metadata": {}} for name in response.get("clusters", [])]
        except AWSIntegrationError as exc:
            logger.warning("AWS inventory EKS collection failed", region=region, error=str(exc))
            return []

    async def _collect_elb(self, session, region: str) -> list[dict]:
        elbv2 = client(session, "elbv2", region)
        try:
            response = await call_aws(elbv2.describe_load_balancers)
            return [{"resource_type": "load_balancer", "resource_id": item["LoadBalancerArn"], "name": item["LoadBalancerName"], "region": region, "metadata": {"type": item.get("Type"), "scheme": item.get("Scheme"), "state": item.get("State", {}).get("Code")}} for item in response.get("LoadBalancers", [])]
        except AWSIntegrationError as exc:
            logger.warning("AWS inventory ELB collection failed", region=region, error=str(exc))
            return []

    async def _collect_iam(self, session, region: str, global_region: str) -> list[dict]:
        iam = client(session, "iam", region)
        resources = []
        try:
            users = await call_aws(iam.list_users)
            resources.extend({"resource_type": "iam_user", "resource_id": item["Arn"], "name": item["UserName"], "region": global_region, "metadata": {"created": str(item.get("CreateDate"))}} for item in users.get("Users", []))
            roles = await call_aws(iam.list_roles)
            resources.extend({"resource_type": "iam_role", "resource_id": item["Arn"], "name": item["RoleName"], "region": global_region, "metadata": {"created": str(item.get("CreateDate"))}} for item in roles.get("Roles", []))
        except AWSIntegrationError as exc:
            logger.warning("AWS inventory IAM collection failed", error=str(exc))
        return resources
