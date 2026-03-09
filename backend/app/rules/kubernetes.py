"""
Kubernetes Analysis Rules
"""

from typing import Any, Dict, List
from app.rules.base import BaseRule, Rule, RuleFinding, Severity, Category, register_rule


@register_rule
class K8sSingleReplicaRule(BaseRule):
    """Check for single replica deployments."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="k8s_single_replica",
            name="Single Replica Deployment",
            description="Deployment has only one replica, creating a single point of failure",
            recommendation="Increase replicas to at least 2 for high availability",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["kubernetes", "deployment", "replicas", "ha"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
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
class K8sNoLivenessProbeRule(BaseRule):
    """Check for missing liveness probes."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="k8s_no_liveness_probe",
            name="Missing Liveness Probe",
            description="Container does not have a liveness probe configured",
            recommendation="Add livenessProbe to detect and restart unhealthy containers",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["kubernetes", "probe", "health"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("kind") != "Deployment":
                continue

            deployment = resource.get("properties", {})
            containers = deployment.get("containers", [])

            for container in containers:
                if not container.get("liveness_probe"):
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Container '{container.get('name')}' has no liveness probe",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=deployment.get("name"),
                        metadata={"container": container.get("name")},
                    ))

        return findings


@register_rule
class K8sNoReadinessProbeRule(BaseRule):
    """Check for missing readiness probes."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="k8s_no_readiness_probe",
            name="Missing Readiness Probe",
            description="Container does not have a readiness probe configured",
            recommendation="Add readinessProbe to ensure traffic is only sent to ready containers",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["kubernetes", "probe", "health"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("kind") != "Deployment":
                continue

            deployment = resource.get("properties", {})
            containers = deployment.get("containers", [])

            for container in containers:
                if not container.get("readiness_probe"):
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Container '{container.get('name')}' has no readiness probe",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=deployment.get("name"),
                        metadata={"container": container.get("name")},
                    ))

        return findings


@register_rule
class K8sNoResourceLimitsRule(BaseRule):
    """Check for missing resource limits."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="k8s_no_resource_limits",
            name="Missing Resource Limits",
            description="Container does not have CPU/memory limits configured",
            recommendation="Set resources.limits.cpu and resources.limits.memory to prevent resource exhaustion",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["kubernetes", "resources", "limits"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("kind") != "Deployment":
                continue

            deployment = resource.get("properties", {})
            containers = deployment.get("containers", [])

            for container in containers:
                resources_config = container.get("resources", {})
                limits = resources_config.get("limits", {})

                if not limits.get("cpu") or not limits.get("memory"):
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

        return findings


@register_rule
class K8sNoResourceRequestsRule(BaseRule):
    """Check for missing resource requests."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="k8s_no_resource_requests",
            name="Missing Resource Requests",
            description="Container does not have CPU/memory requests configured",
            recommendation="Set resources.requests.cpu and resources.requests.memory for proper scheduling",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["kubernetes", "resources", "requests"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("kind") != "Deployment":
                continue

            deployment = resource.get("properties", {})
            containers = deployment.get("containers", [])

            for container in containers:
                resources_config = container.get("resources", {})
                requests = resources_config.get("requests", {})

                if not requests.get("cpu") or not requests.get("memory"):
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Container '{container.get('name')}' has no resource requests",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=deployment.get("name"),
                        metadata={"container": container.get("name")},
                    ))

        return findings


@register_rule
class K8sLatestImageTagRule(BaseRule):
    """Check for latest image tags."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="k8s_latest_image_tag",
            name="Container Uses Latest Image Tag",
            description="Container image uses 'latest' tag, making deployments non-reproducible",
            recommendation="Pin container images to specific version tags",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["kubernetes", "image", "versioning"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("kind") != "Deployment":
                continue

            deployment = resource.get("properties", {})
            containers = deployment.get("containers", [])

            for container in containers:
                image = container.get("image", "")
                if ":latest" in image or ":" not in image:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Container '{container.get('name')}' uses image '{image}' with latest tag",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=deployment.get("name"),
                        metadata={"container": container.get("name"), "image": image},
                    ))

        return findings


@register_rule
class K8sPrivilegedContainerRule(BaseRule):
    """Check for privileged containers."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="k8s_privileged_container",
            name="Privileged Container Detected",
            description="Container runs in privileged mode, increasing security risk",
            recommendation="Remove privileged: true and use specific capabilities instead",
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            tags=["kubernetes", "security", "privileged"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("kind") != "Deployment":
                continue

            deployment = resource.get("properties", {})
            containers = deployment.get("containers", [])

            for container in containers:
                security_context = container.get("security_context", {})
                if security_context.get("privileged"):
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Container '{container.get('name')}' runs in privileged mode",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=deployment.get("name"),
                        metadata={"container": container.get("name")},
                    ))

        return findings


@register_rule
class K8sSecretEnvUsageRule(BaseRule):
    """Check for secrets injected via environment variables."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="k8s_secret_env_usage",
            name="Secret Injected via Environment Variable",
            description="Secrets are injected via environment variables instead of mounted volumes",
            recommendation="Mount secrets using volume mounts instead of environment variables for better security",
            severity=Severity.MEDIUM,
            category=Category.SECURITY,
            tags=["kubernetes", "secrets", "security"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("kind") != "Deployment":
                continue

            deployment = resource.get("properties", {})
            containers = deployment.get("containers", [])

            for container in containers:
                env_vars = container.get("env", [])
                for env in env_vars:
                    value_from = env.get("valueFrom", {})
                    if value_from.get("secretKeyRef"):
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=self.rule.severity,
                            category=self.rule.category,
                            description=f"Secret '{env.get('name')}' injected via environment variable in container '{container.get('name')}'",
                            recommendation="Use volume mounts for secrets:\n\nvolumeMounts:\n  - mountPath: /secrets\n    name: db-secret\n    readOnly: true\nvolumes:\n  - name: db-secret\n    secret:\n      secretName: db-credentials",
                            file_path=file_path,
                            resource_name=deployment.get("name"),
                            metadata={"container": container.get("name"), "secret_env": env.get("name")},
                        ))

        return findings


@register_rule
class K8sNoNetworkPolicyRule(BaseRule):
    """Check for missing NetworkPolicies."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="k8s_no_network_policy",
            name="Missing Network Policies",
            description="No NetworkPolicies found, allowing unrestricted pod-to-pod communication",
            recommendation="Implement NetworkPolicies to restrict traffic between pods",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["kubernetes", "networking", "security"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []
        has_network_policy = False
        has_workload = False

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            kind = resource.get("kind")
            if kind in ["Deployment", "StatefulSet", "DaemonSet", "Pod"]:
                has_workload = True
            if kind == "NetworkPolicy":
                has_network_policy = True
                break

        if has_workload and not has_network_policy:
            findings.append(RuleFinding(
                rule_id=self.rule.id,
                rule_name=self.rule.name,
                severity=self.rule.severity,
                category=self.rule.category,
                description=self.rule.description,
                recommendation=self.rule.recommendation,
                file_path=file_path,
            ))

        return findings


@register_rule
class K8sNoHPARule(BaseRule):
    """Check for missing HorizontalPodAutoscaler."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="k8s_no_hpa",
            name="Missing HorizontalPodAutoscaler",
            description="No HorizontalPodAutoscaler found for scaling workloads",
            recommendation="Configure HPA to automatically scale based on CPU/memory usage or custom metrics",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["kubernetes", "autoscaling", "scalability"],
        )

    def evaluate(self, resources: List[Dict[str, Any]], file_path: str) -> List[RuleFinding]:
        findings = []
        has_hpa = False
        has_deployment = False

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            kind = resource.get("kind")
            if kind == "Deployment":
                has_deployment = True
            if kind == "HorizontalPodAutoscaler":
                has_hpa = True
                break

        if has_deployment and not has_hpa:
            findings.append(RuleFinding(
                rule_id=self.rule.id,
                rule_name=self.rule.name,
                severity=self.rule.severity,
                category=self.rule.category,
                description=self.rule.description,
                recommendation=self.rule.recommendation,
                file_path=file_path,
            ))

        return findings
