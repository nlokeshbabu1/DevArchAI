"""
Observability Rules for Infrastructure Analysis
"""

from typing import Any

from app.rules.base import BaseRule, Category, Rule, RuleFinding, Severity, register_rule


@register_rule
class MissingMonitoringStackRule(BaseRule):
    """Check for missing monitoring stack."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="OBS-001",
            name="Missing Monitoring Stack",
            description="No Prometheus/Grafana monitoring configuration detected",
            recommendation="Deploy Prometheus and Grafana for metrics collection and visualization",
            severity=Severity.MEDIUM,
            category=Category.OBSERVABILITY,
            tags=["kubernetes", "monitoring", "prometheus", "grafana"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        # Check for monitoring resources
        has_prometheus = False
        has_grafana = False
        has_service_monitor = False

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            kind = resource.get("kind", "")
            name = resource.get("name", "").lower()

            if "prometheus" in name or kind == "Prometheus":
                has_prometheus = True
            if "grafana" in name or kind == "Grafana":
                has_grafana = True
            if kind == "ServiceMonitor":
                has_service_monitor = True

        # Check if we have k8s resources but no monitoring
        k8s_resources = [r for r in resources if r.get("file_type") == "kubernetes"]
        if k8s_resources and not (has_prometheus or has_grafana):
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
class MissingLoggingConfigurationRule(BaseRule):
    """Check for missing logging configuration."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="OBS-002",
            name="Missing Logging Configuration",
            description="No centralized logging configuration detected",
            recommendation="Implement centralized logging with ELK stack or similar",
            severity=Severity.MEDIUM,
            category=Category.OBSERVABILITY,
            tags=["kubernetes", "logging", "elk", "fluentd"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        # Check for logging resources
        has_logging = False
        logging_indicators = [
            "fluentd", "fluent-bit", "filebeat", "logstash",
            "elasticsearch", "kibana", "splunk", "loki"
        ]

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            name = resource.get("name", "").lower()
            kind = resource.get("kind", "").lower()

            if any(indicator in name or indicator in kind for indicator in logging_indicators):
                has_logging = True
                break

        # Check Terraform for CloudWatch
        for resource in resources:
            if resource.get("resource_type") == "aws_cloudwatch_log_group":
                has_logging = True

        k8s_resources = [r for r in resources if r.get("file_type") == "kubernetes"]
        if k8s_resources and not has_logging:
            findings.append(RuleFinding(
                rule_id=self.rule.id,
                rule_name=self.rule.name,
                severity=self.rule.severity,
                category=self.rule.category,
                description=self.rule.description,
                recommendation="Deploy Fluentd/Fluent Bit with Elasticsearch or Loki",
                file_path=file_path,
            ))

        return findings


@register_rule
class MissingAlertingRule(BaseRule):
    """Check for missing alerting configuration."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="OBS-003",
            name="Missing Alerting Configuration",
            description="No alerting rules or Alertmanager configuration detected",
            recommendation="Configure Prometheus Alertmanager with appropriate alerting rules",
            severity=Severity.MEDIUM,
            category=Category.OBSERVABILITY,
            tags=["kubernetes", "alerting", "prometheus", "alertmanager"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        has_alerting = False

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            kind = resource.get("kind", "")
            name = resource.get("name", "").lower()

            if "alert" in name or kind in ["PrometheusRule", "Alertmanager"]:
                has_alerting = True
                break

        k8s_resources = [r for r in resources if r.get("file_type") == "kubernetes"]
        if k8s_resources and not has_alerting:
            findings.append(RuleFinding(
                rule_id=self.rule.id,
                rule_name=self.rule.name,
                severity=self.rule.severity,
                category=self.rule.category,
                description=self.rule.description,
                recommendation="Create PrometheusRule resources for critical alerts",
                file_path=file_path,
            ))

        return findings


@register_rule
class MissingDistributedTracingRule(BaseRule):
    """Check for missing distributed tracing."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="OBS-004",
            name="Missing Distributed Tracing",
            description="No distributed tracing configuration detected",
            recommendation="Implement distributed tracing with Jaeger, Zipkin, or AWS X-Ray",
            severity=Severity.LOW,
            category=Category.OBSERVABILITY,
            tags=["kubernetes", "tracing", "jaeger", "x-ray"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        tracing_indicators = ["jaeger", "zipkin", "x-ray", "xray", "tempo"]

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            name = resource.get("name", "").lower()
            kind = resource.get("kind", "").lower()

            if any(indicator in name or indicator in kind for indicator in tracing_indicators):
                return findings  # Tracing found

        k8s_resources = [r for r in resources if r.get("file_type") == "kubernetes"]
        if k8s_resources:
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
class MissingCloudWatchDashboardsRule(BaseRule):
    """Check for missing CloudWatch dashboards."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="OBS-005",
            name="Missing CloudWatch Dashboards",
            description="No CloudWatch dashboard configuration detected",
            recommendation="Create CloudWatch dashboards for key metrics visualization",
            severity=Severity.LOW,
            category=Category.OBSERVABILITY,
            tags=["terraform", "aws", "cloudwatch", "dashboard"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        has_dashboard = False

        for resource in resources:
            if resource.get("resource_type") == "aws_cloudwatch_dashboard":
                has_dashboard = True
                break

        terraform_resources = [r for r in resources if r.get("file_type") == "terraform"]
        if terraform_resources and not has_dashboard:
            findings.append(RuleFinding(
                rule_id=self.rule.id,
                rule_name=self.rule.name,
                severity=self.rule.severity,
                category=self.rule.category,
                description=self.rule.description,
                recommendation="Add aws_cloudwatch_dashboard resources",
                file_path=file_path,
            ))

        return findings


@register_rule
class MissingServiceMapRule(BaseRule):
    """Check for missing service mapping."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="OBS-006",
            name="Missing Service Mapping",
            description="No service mesh or service map configuration detected",
            recommendation="Consider implementing service mesh (Istio, App Mesh) for service discovery",
            severity=Severity.LOW,
            category=Category.OBSERVABILITY,
            tags=["kubernetes", "service-mesh", "istio", "observability"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []

        service_mesh_indicators = ["istio", "linkerd", "consul", "app-mesh", "service-mesh"]

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            name = resource.get("name", "").lower()
            kind = resource.get("kind", "").lower()

            if any(indicator in name or indicator in kind for indicator in service_mesh_indicators):
                return findings  # Service mesh found

        k8s_resources = [r for r in resources if r.get("file_type") == "kubernetes"]
        if len(k8s_resources) >= 3:  # Only flag if there are multiple services
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
