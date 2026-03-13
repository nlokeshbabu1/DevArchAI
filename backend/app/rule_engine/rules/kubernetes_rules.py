"""Kubernetes rules for infrastructure analysis."""

from typing import Any

from app.rule_engine.base import BaseRule, Category, Rule, RuleFinding, Severity, register_rule


@register_rule(file_types=["kubernetes"])
class KubernetesMissingHPARule(BaseRule):
    """Check for missing Horizontal Pod Autoscaler."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-SCALE-001",
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


@register_rule(file_types=["kubernetes"])
class KubernetesMissingResourceLimitsRule(BaseRule):
    """Check for missing resource limits in Kubernetes."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-SCALE-002",
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
                elif not resources_spec.get("limits"):
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


@register_rule(file_types=["kubernetes"])
class KubernetesMissingHealthCheckRule(BaseRule):
    """Check for missing health checks in Kubernetes."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-REL-001",
            name="Missing Health Checks",
            description="Container does not have liveness/readiness probes configured",
            recommendation="Configure liveness and readiness probes for all containers",
            severity=Severity.HIGH,
            category=Category.RELIABILITY,
            tags=["kubernetes", "health", "probe"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("kind") != "Deployment":
                continue

            deployment = resource.get("properties", {})
            containers = deployment.get("containers", [])

            for container in containers:
                has_liveness = container.get("liveness_probe", False)
                has_readiness = container.get("readiness_probe", False)

                if not has_liveness:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=Severity.HIGH,
                        category=self.rule.category,
                        description=f"Container '{container.get('name')}' has no liveness probe",
                        recommendation="Add livenessProbe to detect and restart unhealthy containers",
                        file_path=file_path,
                        resource_name=deployment.get("name"),
                        metadata={"container": container.get("name"), "probe_type": "liveness"},
                    ))

                if not has_readiness:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=Severity.MEDIUM,
                        category=self.rule.category,
                        description=f"Container '{container.get('name')}' has no readiness probe",
                        recommendation="Add readinessProbe to prevent traffic to unready containers",
                        file_path=file_path,
                        resource_name=deployment.get("name"),
                        metadata={"container": container.get("name"), "probe_type": "readiness"},
                    ))

        return findings


@register_rule(file_types=["kubernetes"])
class KubernetesMissingNetworkPolicyRule(BaseRule):
    """Check for missing Kubernetes NetworkPolicies."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-SEC-001",
            name="Missing Network Policies",
            description="No Kubernetes NetworkPolicies found, allowing unrestricted pod-to-pod communication",
            recommendation="Implement NetworkPolicies to restrict traffic between pods",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["kubernetes", "networking", "security"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        has_network_policy = any(
            r.get("kind") == "NetworkPolicy"
            for r in resources
        )

        has_deployment = any(
            r.get("kind") == "Deployment"
            for r in resources
        )

        findings = []

        if has_deployment and not has_network_policy:
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
class KubernetesMissingPodSecurityContextRule(BaseRule):
    """Check for missing pod security contexts."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-SEC-002",
            name="Missing Pod Security Context",
            description="Pods do not have security contexts configured",
            recommendation="Configure podSecurityContext and securityContext to enforce least privilege",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            tags=["kubernetes", "security", "pod"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        for resource in resources:
            if resource.get("kind") != "Deployment":
                continue

            deployment = resource.get("properties", {})
            containers = deployment.get("containers", [])

            for container in containers:
                security_context = container.get("security_context", {})
                if not security_context:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Container '{container.get('name')}' has no security context",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=deployment.get("name"),
                        metadata={"container": container.get("name")},
                    ))

        return findings


@register_rule(file_types=["kubernetes"])
class KubernetesMissingPDBRule(BaseRule):
    """Check for missing Pod Disruption Budget."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="K8S-REL-002",
            name="Missing Pod Disruption Budget",
            description="No PodDisruptionBudget found for deployment",
            recommendation="Create PDB to ensure minimum availability during voluntary disruptions",
            severity=Severity.MEDIUM,
            category=Category.RELIABILITY,
            tags=["kubernetes", "pdb", "availability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        # Collect deployments and PDBs
        deployments = []
        pdb_selectors = []

        for resource in resources:
            if resource.get("kind") == "Deployment":
                deployments.append(resource)
            elif resource.get("kind") == "PodDisruptionBudget":
                pdb_selectors.append(resource.get("properties", {}).get("selector", {}))

        # Check each deployment for PDB coverage
        for deployment in deployments:
            name = deployment.get("name", "")
            labels = deployment.get("properties", {}).get("labels", {})

            has_pdb = any(
                pdb.get("matchLabels", {}).get("app") == labels.get("app")
                for pdb in pdb_selectors
            )

            if not has_pdb:
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


# Note: K8S-OBS-001 (Missing Monitoring) has been moved to repository-level rules
# See: app.rule_engine.repository_rules.RepositoryLevelRules._check_missing_monitoring
# This prevents duplicate findings for each file in the repository
