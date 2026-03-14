"""Repository-level rule evaluation for cross-file analysis."""

from typing import Any

import structlog

from app.rule_engine.base import Category, RuleFinding, Severity

logger = structlog.get_logger(__name__)


class RepositoryLevelRules:
    """
    Repository-level rules that need to scan the entire repository.

    These rules run once per repository, not per file.
    Examples:
    - Missing monitoring stack (should check all files)
    - Missing NetworkPolicy (should check all namespaces)
    - Missing HPA across deployments (should check all deployments)
    """

    def __init__(self):
        self.monitoring_indicators = [
            "prometheus",
            "grafana",
            "kube-prometheus",
            "prometheus-operator",
            "opentelemetry",
            "otel",
            "loki",
            "jaeger",
            "zipkin",
            "datadog",
            "newrelic",
            "dynatrace",
            "servicemonitor",
            "podmonitor",
            "prometheusrule",
            "alertmanager",
        ]

    def evaluate_repository_level_rules(
        self,
        parsed_files: list,
        all_resources: list[dict[str, Any]],
    ) -> list[RuleFinding]:
        """
        Evaluate all repository-level rules.

        Args:
            parsed_files: List of all parsed files in repository
            all_resources: List of all extracted resources

        Returns:
            List of findings (one per repo-level issue)
        """
        findings = []

        # Run each repo-level rule once
        findings.extend(self._check_missing_monitoring(all_resources))
        findings.extend(self._check_missing_network_policy(all_resources))
        findings.extend(self._check_missing_hpa_coverage(all_resources))

        return findings

    def _check_missing_monitoring(
        self,
        all_resources: list[dict[str, Any]],
    ) -> list[RuleFinding]:
        """
        Check if repository has any monitoring stack.

        Scans entire repository for monitoring indicators.
        Creates ONE finding if none found.
        """
        # Collect all resource names and kinds
        all_names = []
        all_kinds = []

        for resource in all_resources:
            name = resource.get("name", "").lower()
            kind = resource.get("kind", "").lower()
            all_names.append(name)
            all_kinds.append(kind)

            # Check properties for monitoring-related content
            properties = resource.get("properties", {})
            if isinstance(properties, dict):
                # Check container images
                containers = properties.get("containers", [])
                for container in containers:
                    if isinstance(container, dict):
                        image = container.get("image", "").lower()
                        all_names.append(image)

        # Check if any monitoring indicator is present
        all_text = " ".join(all_names + all_kinds)

        has_monitoring = any(
            indicator in all_text
            for indicator in self.monitoring_indicators
        )

        if not has_monitoring:
            return [RuleFinding(
                rule_id="K8S-OBS-001",
                rule_name="Missing Monitoring Stack",
                severity=Severity.HIGH,
                category=Category.OBSERVABILITY,
                description="No monitoring stack (Prometheus/Grafana/OpenTelemetry) detected in repository",
                recommendation="Deploy monitoring stack using Prometheus Operator, kube-prometheus-stack, or managed solutions like Datadog/New Relic",
                file_path="repository-level",
                resource_name="Entire Repository",
                metadata={
                    "scope": "repository",
                    "checked_indicators": len(self.monitoring_indicators),
                    "recommendation_detail": "Consider using helm chart: prometheus-community/kube-prometheus-stack",
                },
            )]

        return []

    def _check_missing_network_policy(
        self,
        all_resources: list[dict[str, Any]],
    ) -> list[RuleFinding]:
        """
        Check if repository has NetworkPolicy resources.

        Scans entire repository for NetworkPolicy.
        Creates ONE finding if none found AND there are deployments.
        """
        has_network_policy = False
        has_deployments = False

        for resource in all_resources:
            kind = resource.get("kind", "").lower()
            if kind == "networkpolicy":
                has_network_policy = True
                break
            elif kind in ["deployment", "statefulset", "daemonset"]:
                has_deployments = True

        # Only flag if there are workloads but no network policies
        if has_deployments and not has_network_policy:
            return [RuleFinding(
                rule_id="K8S-SEC-003",
                rule_name="Missing NetworkPolicy",
                severity=Severity.MEDIUM,
                category=Category.SECURITY,
                description="No NetworkPolicy resources found in repository with deployments",
                recommendation="Create NetworkPolicy resources to control pod-to-pod communication and implement zero-trust networking",
                file_path="repository-level",
                resource_name="Entire Repository",
                metadata={
                    "scope": "repository",
                    "recommendation_detail": "Start with default-deny policies and gradually allow required traffic",
                },
            )]

        return []

    def _check_missing_hpa_coverage(
        self,
        all_resources: list[dict[str, Any]],
    ) -> list[RuleFinding]:
        """
        Check if deployments have HPA coverage.

        This is a repo-level check that compares all deployments against all HPAs.
        Creates ONE aggregated finding if coverage is missing.
        """
        deployments = []
        hpa_targets = set()

        for resource in all_resources:
            kind = resource.get("kind", "").lower()
            if kind == "deployment":
                name = resource.get("name", "")
                deployments.append(name)
            elif kind == "horizontalpodautoscaler":
                # Extract target reference
                spec = resource.get("properties", {}).get("spec", {})
                if isinstance(spec, dict):
                    target_ref = spec.get("scaleTargetRef", {})
                    target_name = target_ref.get("name", "")
                    target_kind = target_ref.get("kind", "Deployment")
                    hpa_targets.add(f"{target_kind}/{target_name}")

        # Check coverage
        uncovered = []
        for deployment in deployments:
            if f"Deployment/{deployment}" not in hpa_targets:
                uncovered.append(deployment)

        # Only create finding if there are uncovered deployments
        if uncovered:
            return [RuleFinding(
                rule_id="K8S-SCALE-001",
                rule_name="Missing Horizontal Pod Autoscaler",
                severity=Severity.HIGH,
                category=Category.SCALABILITY,
                description=f"{len(uncovered)} deployment(s) without HPA: {', '.join(uncovered[:5])}{'...' if len(uncovered) > 5 else ''}",
                recommendation="Create HorizontalPodAutoscaler resources for automatic scaling based on CPU/memory metrics",
                file_path="repository-level",
                resource_name="Entire Repository",
                metadata={
                    "scope": "repository",
                    "uncovered_count": len(uncovered),
                    "uncovered_deployments": uncovered,
                    "recommendation_detail": "Use metrics-server for resource metrics or Prometheus adapter for custom metrics",
                },
            )]

        return []


# Global instance
repo_level_rules = RepositoryLevelRules()
