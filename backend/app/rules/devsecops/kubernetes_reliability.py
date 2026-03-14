"""
Kubernetes Reliability Rules - DevSecOps Rule Set (K8S-REL-001 to K8S-REL-010)

Production-grade Kubernetes reliability scanning rules for DevArchAI.
"""

from typing import Any

from app.rules.base import BaseRule, Category, Rule, RuleFinding, Severity, register_rule


@register_rule(file_types=["kubernetes"])
class K8sMissingHPARule(BaseRule):
    """K8S-REL-001: Check for missing HorizontalPodAutoscaler."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-REL-001",
            name="Missing Horizontal Pod Autoscaler",
            description="No HorizontalPodAutoscaler found for automatic scaling based on resource utilization",
            recommendation="Configure HPA for automatic scaling:\n\napiVersion: autoscaling/v2\nkind: HorizontalPodAutoscaler\nmetadata:\n  name: app-hpa\nspec:\n  scaleTargetRef:\n    apiVersion: apps/v1\n    kind: Deployment\n    name: app\n  minReplicas: 2\n  maxReplicas: 10\n  metrics:\n  - type: Resource\n    resource:\n      name: cpu\n      target:\n        type: Utilization\n        averageUtilization: 70",
            severity=Severity.HIGH,
            category=Category.SCALABILITY,
            tags=["kubernetes", "autoscaling", "hpa", "scalability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        has_hpa = False
        has_deployment = False
        deployment_names = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            kind = resource.get("kind")
            name = resource.get("name", "")

            if kind == "HorizontalPodAutoscaler":
                has_hpa = True
            elif kind == "Deployment":
                has_deployment = True
                deployment_names.append(name)

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


@register_rule(file_types=["kubernetes"])
class K8sMissingPDBRule(BaseRule):
    """K8S-REL-002: Check for missing Pod Disruption Budget."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-REL-002",
            name="Missing Pod Disruption Budget",
            description="No PodDisruptionBudget found to protect availability during voluntary disruptions",
            recommendation="Create PDB for critical workloads:\n\napiVersion: policy/v1\nkind: PodDisruptionBudget\nmetadata:\n  name: app-pdb\nspec:\n  minAvailable: 1\n  selector:\n    matchLabels:\n      app: my-app",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["kubernetes", "pdb", "reliability", "availability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        has_pdb = False
        has_deployment = False

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            kind = resource.get("kind")

            if kind == "PodDisruptionBudget":
                has_pdb = True
            elif kind in ["Deployment", "StatefulSet"]:
                has_deployment = True

        if has_deployment and not has_pdb:
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


@register_rule(file_types=["kubernetes"])
class K8sMissingReplicaConfigRule(BaseRule):
    """K8S-REL-003: Check for missing or inadequate replica configuration."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-REL-003",
            name="Missing Replica Configuration",
            description="Deployments should have multiple replicas for high availability",
            recommendation="Set replicas to at least 2 for production workloads:\n\nspec:\n  replicas: 3",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["kubernetes", "replicas", "ha", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") == "Deployment":
                replicas = resource.get("properties", {}).get("replicas", 1)

                if replicas < 2:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Deployment has {replicas} replica(s), minimum 2 recommended for HA",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=resource.get("name"),
                        metadata={"replicas": replicas},
                    ))

        return findings


@register_rule(file_types=["kubernetes"])
class K8sNoRollingUpdateStrategyRule(BaseRule):
    """K8S-REL-004: Check for missing rolling update strategy."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-REL-004",
            name="No Rolling Update Strategy",
            description="Deployment does not have a rolling update strategy configured for zero-downtime deployments",
            recommendation="Configure rolling update strategy:\n\nstrategy:\n  type: RollingUpdate\n  rollingUpdate:\n    maxSurge: 1\n    maxUnavailable: 0",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["kubernetes", "deployment", "strategy", "rolling-update"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") == "Deployment":
                strategy = resource.get("properties", {}).get("strategy", {})
                strategy_type = strategy.get("type", "RollingUpdate")

                if strategy_type == "Recreate":
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description="Deployment uses Recreate strategy, causing downtime during updates",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=resource.get("name"),
                    ))
                elif not strategy:
                    # Default RollingUpdate may not be optimal
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=Severity.LOW,
                        category=self.rule.category,
                        description="Deployment uses default rolling update strategy",
                        recommendation="Explicitly configure rolling update parameters for controlled deployments",
                        file_path=file_path,
                        resource_name=resource.get("name"),
                    ))

        return findings


@register_rule(file_types=["kubernetes"])
class K8sMissingResourceRequestsRule(BaseRule):
    """K8S-REL-005: Check for missing resource requests."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-REL-005",
            name="Missing Resource Requests",
            description="Pods without resource requests may not be scheduled optimally",
            recommendation="Set resource requests for proper scheduling:\n\nresources:\n  requests:\n    memory: \"256Mi\"\n    cpu: \"250m\"",
            severity=Severity.MEDIUM,
            category=Category.SCALABILITY,
            tags=["kubernetes", "resources", "requests", "scheduling"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") in ["Deployment", "Pod", "DaemonSet", "StatefulSet", "Job"]:
                containers = resource.get("properties", {}).get("containers", [])

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
                            resource_name=container.get("name"),
                            metadata={"container": container.get("name")},
                        ))

        return findings


@register_rule(file_types=["kubernetes"])
class K8sSingleReplicaDeploymentRule(BaseRule):
    """K8S-REL-006: Check for single replica deployments."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-REL-006",
            name="Single Replica Deployment",
            description="Deployment has only one replica, creating a single point of failure",
            recommendation="Increase replicas to at least 2 for high availability:\n\nspec:\n  replicas: 2",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["kubernetes", "replicas", "ha", "reliability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") == "Deployment":
                replicas = resource.get("properties", {}).get("replicas", 1)

                if replicas == 1:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=self.rule.description,
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=resource.get("name"),
                        metadata={"replicas": replicas},
                    ))

        return findings


@register_rule(file_types=["kubernetes"])
class K8sMissingAntiAffinityRule(BaseRule):
    """K8S-REL-007: Check for missing pod anti-affinity rules."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-REL-007",
            name="Missing Anti-Affinity Rules",
            description="No pod anti-affinity configured, replicas may be scheduled on same node",
            recommendation="Add pod anti-affinity to spread replicas:\n\naffinity:\n  podAntiAffinity:\n    requiredDuringSchedulingIgnoredDuringExecution:\n    - labelSelector:\n        matchLabels:\n          app: my-app\n      topologyKey: kubernetes.io/hostname",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["kubernetes", "affinity", "ha", "scheduling"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") == "Deployment":
                replicas = resource.get("properties", {}).get("replicas", 1)
                affinity = resource.get("properties", {}).get("affinity", {})

                # Only flag if multiple replicas without anti-affinity
                if replicas > 1 and not affinity:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Deployment '{resource.get('name')}' has {replicas} replicas but no anti-affinity rules",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=resource.get("name"),
                        metadata={"replicas": replicas},
                    ))

        return findings


@register_rule(file_types=["kubernetes"])
class K8sMissingNodeSelectorRule(BaseRule):
    """K8S-REL-008: Check for missing node selector or node affinity."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-REL-008",
            name="Missing Node Selector",
            description="No node selector or node affinity configured for workload placement control",
            recommendation="Add node selector or affinity for controlled placement:\n\nnodeSelector:\n  disktype: ssd\n\n# Or use node affinity for more flexibility",
            severity=Severity.LOW,
            category=Category.RELIABILITY,
            tags=["kubernetes", "node-selector", "scheduling"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") in ["Deployment", "Pod", "DaemonSet", "StatefulSet"]:
                node_selector = resource.get("properties", {}).get("node_selector")
                affinity = resource.get("properties", {}).get("affinity", {})
                node_affinity = affinity.get("node_affinity") if affinity else None

                if not node_selector and not node_affinity:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=self.rule.description,
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=resource.get("name"),
                    ))

        return findings


@register_rule(file_types=["kubernetes"])
class K8sMissingStartupProbeRule(BaseRule):
    """K8S-REL-009: Check for missing startup probe."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-REL-009",
            name="Missing Startup Probe",
            description="No startup probe configured for slow-starting containers",
            recommendation="Add startup probe for applications with slow startup:\n\nstartupProbe:\n  httpGet:\n    path: /healthz\n    port: 8080\n  failureThreshold: 30\n  periodSeconds: 10",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["kubernetes", "probe", "startup", "health"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") in ["Deployment", "Pod", "DaemonSet", "StatefulSet"]:
                containers = resource.get("properties", {}).get("containers", [])

                for container in containers:
                    has_liveness = container.get("liveness_probe") is not None
                    has_readiness = container.get("readiness_probe") is not None
                    has_startup = container.get("startup_probe") is not None

                    # Flag if has other probes but no startup probe
                    # (indicates app needs health checks but may have slow startup)
                    if (has_liveness or has_readiness) and not has_startup:
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=self.rule.severity,
                            category=self.rule.category,
                            description=f"Container '{container.get('name')}' has health probes but no startup probe",
                            recommendation=self.rule.recommendation,
                            file_path=file_path,
                            resource_name=container.get("name"),
                            metadata={"container": container.get("name")},
                        ))

        return findings


@register_rule(file_types=["kubernetes"])
class K8sMissingServiceRule(BaseRule):
    """K8S-REL-010: Check for missing Service definition."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-REL-010",
            name="Service Not Defined",
            description="Deployment exists without corresponding Service for network access",
            recommendation="Create a Service to expose your deployment:\n\napiVersion: v1\nkind: Service\nmetadata:\n  name: my-app-service\nspec:\n  selector:\n    app: my-app\n  ports:\n  - port: 80\n    targetPort: 8080\n  type: ClusterIP",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["kubernetes", "service", "networking"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        deployment_names = set()
        service_names = set()
        service_selectors = []

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            kind = resource.get("kind")
            name = resource.get("name", "")
            properties = resource.get("properties", {})

            if kind == "Deployment":
                deployment_names.add(name)
                # Get selector labels
                selector = properties.get("selector", {})
                match_labels = selector.get("matchLabels", {})
                if match_labels:
                    service_selectors.append((name, match_labels))
            elif kind == "Service":
                service_names.add(name)
                selector = properties.get("selector", {})
                if selector:
                    service_selectors.append((name, selector))

        # Check if deployments have matching services
        for dep_name, dep_labels in service_selectors:
            if dep_name in deployment_names:
                # Check if any service selects this deployment
                has_matching_service = False
                for svc_name, svc_selector in service_selectors:
                    if svc_name != dep_name:
                        # Check if service selector matches deployment labels
                        if all(dep_labels.get(k) == v for k, v in svc_selector.items()):
                            has_matching_service = True
                            break

                if not has_matching_service:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Deployment '{dep_name}' has no matching Service",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=dep_name,
                    ))

        return findings
