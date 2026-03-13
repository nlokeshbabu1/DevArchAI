"""
Scalability Rules for Infrastructure Analysis
"""

from typing import Any

from app.rules.base import BaseRule, Category, Rule, RuleFinding, Severity, register_rule


@register_rule
class MissingHPARule(BaseRule):
    """Check for missing Horizontal Pod Autoscaler."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="SCALE-001",
            name="Missing Horizontal Pod Autoscaler",
            description="Deployment does not have an associated HorizontalPodAutoscaler for automatic scaling",
            recommendation="Create an HPA resource to enable automatic scaling based on CPU/memory metrics",
            severity=Severity.HIGH,
            category=Category.SCALABILITY,
            tags=["kubernetes", "scaling", "hpa"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        # Collect all deployments and HPAs
        deployments = []
        hpa_targets = set()

        for resource in resources:
            if resource.get("file_type") == "kubernetes":
                if resource.get("kind") == "Deployment":
                    deployments.append(resource)
                elif resource.get("kind") == "HorizontalPodAutoscaler":
                    target = resource.get("properties", {}).get("target_ref", {})
                    hpa_targets.add(f"{target.get('kind', '')}/{target.get('name', '')}")

        # Check each deployment for HPA
        for deployment in deployments:
            name = deployment.get("name", "")
            if f"Deployment/{name}" not in hpa_targets:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    resource_name=name,
                ))

        return findings


@register_rule
class MissingResourceLimitsRule(BaseRule):
    """Check for missing resource limits in Kubernetes."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="SCALE-002",
            name="Missing Resource Limits",
            description="Container does not have CPU/memory limits defined",
            recommendation="Define resource requests and limits for all containers",
            severity=Severity.HIGH,
            category=Category.SCALABILITY,
            tags=["kubernetes", "resources", "limits"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("kind") != "Deployment":
                continue

            deployment = resource.get("properties", {})
            containers = deployment.get("containers", [])

            for container in containers:
                resources_spec = container.get("resources", {})

                if not resources_spec:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Container '{container.get('name')}' has no resource limits",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=deployment.get("name"),
                        metadata={"container": container.get("name")},
                    ))
                else:
                    if not resources_spec.get("limits"):
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=Severity.MEDIUM,
                            category=self.rule.category,
                            description=f"Container '{container.get('name')}' has no resource limits (only requests)",
                            recommendation="Add resource limits in addition to requests",
                            file_path=file_path,
                            resource_name=deployment.get("name"),
                            metadata={"container": container.get("name")},
                        ))

        return findings


@register_rule
class SingleReplicaDeploymentRule(BaseRule):
    """Check for single replica deployments."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="SCALE-003",
            name="Single Replica Deployment",
            description="Deployment has only one replica, limiting scalability and availability",
            recommendation="Increase replica count to at least 2 for production workloads",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["kubernetes", "scaling", "replicas"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("kind") != "Deployment":
                continue

            deployment = resource.get("properties", {})
            replicas = deployment.get("replicas", 1)

            if replicas == 1:
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    resource_name=deployment.get("name"),
                    metadata={"replicas": replicas},
                ))

        return findings


@register_rule
class MissingLoadBalancerRule(BaseRule):
    """Check for missing load balancer configuration."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="SCALE-004",
            name="Missing Load Balancer",
            description="Service uses ClusterIP instead of LoadBalancer for external traffic",
            recommendation="Use LoadBalancer service type or Ingress for production traffic",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["kubernetes", "networking", "load-balancer"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("kind") != "Service":
                continue

            service = resource.get("properties", {})
            service_type = service.get("type", "ClusterIP")
            ports = service.get("ports", [])

            # Check if it's an external-facing service without LoadBalancer
            if service_type == "ClusterIP" and ports:
                # Check if any port is commonly used for external traffic
                external_ports = [80, 443, 8080, 8443]
                for port in ports:
                    if port.get("port") in external_ports:
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=self.rule.severity,
                            category=self.rule.category,
                            description=self.rule.description,
                            recommendation=self.rule.recommendation,
                            file_path=file_path,
                            resource_name=service.get("name"),
                            metadata={"port": port.get("port")},
                        ))
                        break

        return findings


@register_rule
class DockerLatestTagRule(BaseRule):
    """Check for use of 'latest' tag in Docker images."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="SCALE-005",
            name="Using Latest Tag",
            description="Dockerfile uses 'latest' tag which can cause inconsistent deployments",
            recommendation="Pin base images to specific versions for reproducible builds",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["docker", "image", "versioning"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "dockerfile":
                continue

            base_image = resource.get("base_image", {})
            if base_image and base_image.get("is_latest"):
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=f"Base image '{base_image.get('full')}' uses latest tag",
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    metadata={"image": base_image.get("full")},
                ))

        return findings


@register_rule
class MissingAffinityRulesRule(BaseRule):
    """Check for missing pod affinity/anti-affinity rules."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="SCALE-006",
            name="Missing Affinity Rules",
            description="Deployment has no affinity rules for optimal pod distribution",
            recommendation="Configure pod affinity/anti-affinity for better distribution across nodes",
            severity=Severity.LOW,
            category=Category.SCALABILITY,
            tags=["kubernetes", "scheduling", "affinity"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("kind") != "Deployment":
                continue

            deployment = resource.get("properties", {})

            # Check for affinity configuration
            # This would need deeper parsing of the deployment spec
            # For now, we flag if no affinity is mentioned
            raw_spec = str(deployment)
            if "affinity" not in raw_spec.lower():
                findings.append(RuleFinding(
                    rule_id=self.rule.id,
                    rule_name=self.rule.name,
                    severity=self.rule.severity,
                    category=self.rule.category,
                    description=self.rule.description,
                    recommendation=self.rule.recommendation,
                    file_path=file_path,
                    resource_name=deployment.get("name"),
                ))

        return findings
