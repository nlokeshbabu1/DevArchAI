"""
Cost Optimization Rules for Infrastructure Analysis
"""

from typing import Any, Dict, List
from app.rules.base import BaseRule, Rule, RuleFinding, Severity, Category, register_rule


@register_rule
class MissingSpotInstanceRule(BaseRule):
    """Check for missing spot instance usage."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="COST-001",
            name="Missing Spot Instance Usage",
            description="Workloads may be running on on-demand instances instead of spot instances",
            recommendation="Consider using spot instances for fault-tolerant workloads to reduce costs by up to 90%",
            severity=Severity.LOW,
            category=Category.COST,
            tags=["terraform", "aws", "ec2", "cost-optimization"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("resource_type") not in ["aws_instance", "aws_eks_node_group"]:
                continue

            resource_data = resource.get("properties", {})
            raw_body = resource_data.get("raw_body", "")

            # Check for spot configuration
            if "spot" not in raw_body.lower() and "instance_market_options" not in raw_body:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    resource_name=resource_data.get("name"),
                ))

        return findings


@register_rule
class OverprovisionedResourcesRule(BaseRule):
    """Check for potentially overprovisioned resources."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="COST-002",
            name="Potentially Overprovisioned Resources",
            description="Instance type may be larger than needed for the workload",
            recommendation="Right-size instances based on actual usage metrics",
            severity=Severity.MEDIUM,
            category=Category.COST,
            tags=["terraform", "aws", "cost-optimization", "rightsizing"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        # Large instance families that might be overprovisioned
        large_instances = [
            "m5.4xlarge", "m5.8xlarge", "m5.12xlarge",
            "c5.4xlarge", "c5.9xlarge",
            "r5.4xlarge", "r5.8xlarge",
        ]

        for resource in resources:
            if resource.get("resource_type") != "aws_instance":
                continue

            resource_data = resource.get("properties", {})
            raw_body = resource_data.get("raw_body", "")

            # Check for large instance types
            for instance_type in large_instances:
                if instance_type in raw_body:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Instance type {instance_type} may be overprovisioned",
                        recommendation="Use CloudWatch metrics to right-size instances",
                        file_path=file_path,
                        resource_name=resource_data.get("name"),
                        metadata={"instance_type": instance_type},
                    ))
                    break

        return findings


@register_rule
class MissingS3LifecycleRule(BaseRule):
    """Check for missing S3 lifecycle policies."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="COST-003",
            name="Missing S3 Lifecycle Policy",
            description="S3 bucket does not have lifecycle policies for cost optimization",
            recommendation="Configure lifecycle rules to transition old objects to cheaper storage classes",
            severity=Severity.LOW,
            category=Category.COST,
            tags=["terraform", "aws", "s3", "cost-optimization"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("resource_type") != "aws_s3_bucket":
                continue

            resource_data = resource.get("properties", {})
            raw_body = resource_data.get("raw_body", "")

            # Check for lifecycle configuration
            if "lifecycle" not in raw_body.lower():
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation="Add lifecycle rules to transition objects to IA/Glacier",
                    file_path=file_path,
                    resource_name=resource_data.get("name"),
                ))

        return findings


@register_rule
class MissingReservedCapacityRule(BaseRule):
    """Check for missing reserved capacity planning."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="COST-004",
            name="No Reserved Capacity Planning",
            description="No evidence of reserved capacity or savings plans for predictable workloads",
            recommendation="Consider Reserved Instances or Savings Plans for steady-state workloads",
            severity=Severity.LOW,
            category=Category.COST,
            tags=["terraform", "aws", "cost-optimization", "reserved-instances"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        # This is a meta-rule that would require analysis across multiple resources
        # For now, we flag if there are multiple similar instances
        findings = []

        instance_count = 0
        for resource in resources:
            if resource.get("resource_type") == "aws_instance":
                instance_count += 1

        if instance_count >= 3:
            findings.append(RuleFinding(
                rule_id=self.rule.id,
                rule_name=self.rule.name,
                severity=self.rule.severity,
                category=self.rule.category,
                description=f"Found {instance_count} EC2 instances without reserved capacity",
                recommendation="Evaluate Reserved Instances for cost savings",
                file_path=file_path,
            ))

        return findings


@register_rule
class DockerImageSizeRule(BaseRule):
    """Check for potentially large Docker images."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="COST-005",
            name="Large Base Image",
            description="Using a large base image increases storage and transfer costs",
            recommendation="Use smaller base images like Alpine or distroless to reduce size",
            severity=Severity.LOW,
            category=Category.COST,
            tags=["docker", "image", "cost-optimization"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        # Large base images
        large_images = ["ubuntu", "debian", "centos", "amazonlinux"]

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            base_image = resource.get("base_image", {})
            repository = base_image.get("repository", "").lower()

            if any(large in repository for large in large_images):
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=f"Base image '{base_image.get('full')}' may be large",
                    recommendation="Consider using Alpine or distroless base images",
                    file_path=file_path,
                    metadata={"base_image": base_image.get("full")},
                ))

        return findings
