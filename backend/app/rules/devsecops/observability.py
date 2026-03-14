"""
Observability Rules - DevSecOps Rule Set (OBS-001 to OBS-010)

Production-grade observability scanning rules for DevArchAI.
"""

from typing import Any

from app.rules.base import BaseRule, Category, Rule, RuleFinding, Severity, register_rule


@register_rule(file_types=["kubernetes", "terraform"])
class ObsMissingMonitoringStackRule(BaseRule):
    """OBS-001: Check for missing monitoring stack."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="OBS-001",
            name="Missing Monitoring Stack",
            description="No Prometheus/Grafana monitoring configuration detected for metrics collection",
            recommendation="Deploy monitoring stack:\n\n# Prometheus + Grafana\napiVersion: monitoring.coreos.com/v1\nkind: Prometheus\nmetadata:\n  name: k8s\nspec:\n  replicas: 2\n  serviceMonitorSelector: {}",
            severity=Severity.MEDIUM,
            category=Category.OBSERVABILITY,
            tags=["kubernetes", "monitoring", "prometheus", "grafana"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        has_prometheus = False
        has_grafana = False
        has_service_monitor = False
        has_workload = False

        for resource in resources:
            file_type = resource.get("file_type")
            kind = resource.get("kind", "")
            name = resource.get("name", "").lower()
            resource_type = resource.get("resource_type", "")

            if file_type == "kubernetes":
                if "prometheus" in name or kind == "Prometheus":
                    has_prometheus = True
                if "grafana" in name or kind == "Grafana":
                    has_grafana = True
                if kind == "ServiceMonitor":
                    has_service_monitor = True
                if kind in ["Deployment", "Pod", "Service"]:
                    has_workload = True

            if file_type == "terraform":
                if "prometheus" in resource_type or "grafana" in resource_type:
                    has_prometheus = True
                    has_grafana = True

        if has_workload and not (has_prometheus or has_grafana):
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


@register_rule(file_types=["kubernetes", "terraform"])
class ObsMissingMetricsEndpointRule(BaseRule):
    """OBS-002: Check for missing metrics endpoint."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="OBS-002",
            name="Missing Metrics Endpoint",
            description="Applications do not expose metrics endpoints for monitoring",
            recommendation="Add metrics endpoint to applications:\n\n# Python (Prometheus)\nfrom prometheus_client import start_http_server\nstart_http_server(8000)\n\n# Add /metrics endpoint",
            severity=Severity.MEDIUM,
            category=Category.OBSERVABILITY,
            tags=["kubernetes", "metrics", "prometheus", "monitoring"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        metrics_indicators = [
            "prometheus", "metrics", "/metrics", "metrics-port",
            "monitoring", "telemetry", "opentelemetry", "otel",
        ]

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") in ["Deployment", "Pod", "Service"]:
                containers = resource.get("properties", {}).get("containers", [])
                ports = resource.get("properties", {}).get("ports", [])

                has_metrics = False

                # Check container ports
                for container in containers:
                    container_ports = container.get("ports", [])
                    for port in container_ports:
                        port_name = str(port.get("name", "")).lower()
                        if any(ind in port_name for ind in metrics_indicators):
                            has_metrics = True
                            break

                    # Check environment variables for metrics config
                    env_vars = container.get("env", [])
                    for env in env_vars:
                        env_name = str(env.get("name", "")).lower()
                        if "metrics" in env_name or "prometheus" in env_name:
                            has_metrics = True
                            break

                # Check service ports
                for port in ports:
                    port_name = str(port.get("name", "")).lower()
                    port_num = port.get("port", 0)
                    if any(ind in port_name for ind in metrics_indicators) or port_num == 9090:
                        has_metrics = True
                        break

                if not has_metrics and containers:
                    findings.append(RuleFinding(
                        rule_id=self.rule.id,
                        rule_name=self.rule.name,
                        severity=self.rule.severity,
                        category=self.rule.category,
                        description=f"Workload '{resource.get('name')}' does not expose metrics endpoint",
                        recommendation=self.rule.recommendation,
                        file_path=file_path,
                        resource_name=resource.get("name"),
                    ))

        return findings


@register_rule(file_types=["kubernetes", "terraform"])
class ObsMissingLoggingRule(BaseRule):
    """OBS-003: Check for missing centralized logging."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="OBS-003",
            name="Missing Centralized Logging",
            description="No centralized logging configuration detected for log aggregation",
            recommendation="Implement centralized logging:\n\n# Deploy Fluentd/Fluent Bit\napiVersion: apps/v1\nkind: DaemonSet\nmetadata:\n  name: fluent-bit\nspec:\n  template:\n    spec:\n      containers:\n      - name: fluent-bit\n        image: fluent/fluent-bit",
            severity=Severity.MEDIUM,
            category=Category.OBSERVABILITY,
            tags=["kubernetes", "logging", "elk", "fluentd", "loki"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        logging_indicators = [
            "fluentd", "fluent-bit", "filebeat", "logstash",
            "elasticsearch", "kibana", "splunk", "loki",
            "cloudwatch", "stackdriver", "azure monitor",
            "datadog", "newrelic", "sumo",
        ]

        has_logging = False
        has_workload = False

        for resource in resources:
            file_type = resource.get("file_type")
            kind = resource.get("kind", "")
            name = resource.get("name", "").lower()
            resource_type = resource.get("resource_type", "")

            if file_type == "kubernetes":
                if kind in ["Deployment", "Pod", "DaemonSet"]:
                    has_workload = True
                if any(ind in name or ind in kind.lower() for ind in logging_indicators):
                    has_logging = True

            if file_type == "terraform":
                if any(ind in resource_type for ind in logging_indicators):
                    has_logging = True
                # Check for CloudWatch log groups
                if resource_type == "aws_cloudwatch_log_group":
                    has_logging = True

        if has_workload and not has_logging:
            findings.append(RuleFinding(
                rule_id=self.rule.id,
                rule_name=self.rule.name,
                severity=self.rule.severity,
                category=self.rule.category,
                description=self.rule.description,
                recommendation="Deploy centralized logging:\n\n# Option 1: EFK Stack\nhelm install fluent-bit fluent/fluent-bit\nhelm install elasticsearch elastic/elasticsearch\n\n# Option 2: Loki + Promtail\nhelm install loki grafana/loki-stack\n\n# Option 3: Managed services\n# - AWS CloudWatch Logs\n# - Google Cloud Logging\n# - Azure Monitor Logs",
                file_path=file_path,
            ))

        return findings


@register_rule(file_types=["kubernetes", "terraform"])
class ObsMissingTracingRule(BaseRule):
    """OBS-004: Check for missing distributed tracing."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="OBS-004",
            name="Missing Distributed Tracing",
            description="No distributed tracing configuration detected for request tracking",
            recommendation="Implement distributed tracing:\n\n# Jaeger\napiVersion: jaegertracing.io/v1\nkind: Jaeger\nmetadata:\n  name: my-jaeger\nspec:\n  strategy: production",
            severity=Severity.LOW,
            category=Category.OBSERVABILITY,
            tags=["kubernetes", "tracing", "jaeger", "zipkin", "x-ray"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        tracing_indicators = [
            "jaeger", "zipkin", "x-ray", "xray", "tempo",
            "opentelemetry", "otel", "honeycomb", "lightstep",
            "trace", "tracing", "span",
        ]

        has_tracing = False
        has_microservices = False
        service_count = 0

        for resource in resources:
            file_type = resource.get("file_type")
            kind = resource.get("kind", "")
            name = resource.get("name", "").lower()

            if file_type == "kubernetes":
                if kind in ["Deployment", "Service"]:
                    service_count += 1
                if any(ind in name or ind in kind.lower() for ind in tracing_indicators):
                    has_tracing = True

        has_microservices = service_count >= 2

        if has_microservices and not has_tracing:
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


@register_rule(file_types=["kubernetes", "terraform"])
class ObsMissingAlertingRule(BaseRule):
    """OBS-005: Check for missing alerting configuration."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="OBS-005",
            name="Missing Alerting Configuration",
            description="No alerting rules or Alertmanager configuration detected",
            recommendation="Configure alerting:\n\napiVersion: monitoring.coreos.com/v1\nkind: PrometheusRule\nmetadata:\n  name: alerts\nspec:\n  groups:\n  - name: critical\n    rules:\n    - alert: HighErrorRate\n      expr: rate(http_requests_total{status=~'5..'}[5m]) > 0.1",
            severity=Severity.MEDIUM,
            category=Category.OBSERVABILITY,
            tags=["kubernetes", "alerting", "prometheus", "alertmanager"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        has_alerting = False
        has_monitoring = False

        for resource in resources:
            file_type = resource.get("file_type")
            kind = resource.get("kind", "")
            name = resource.get("name", "").lower()

            if file_type == "kubernetes":
                if kind in ["PrometheusRule", "Alertmanager"]:
                    has_alerting = True
                if "prometheus" in name or kind == "Prometheus":
                    has_monitoring = True
                if "alert" in name:
                    has_alerting = True

        if has_monitoring and not has_alerting:
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


@register_rule(file_types=["kubernetes", "dockerfile"])
class ObsMissingHealthEndpointRule(BaseRule):
    """OBS-006: Check for missing health endpoints."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="OBS-006",
            name="No Health Endpoints",
            description="Applications do not expose health check endpoints for monitoring",
            recommendation="Add health endpoints to applications:\n\n# Express.js\napp.get('/health', (req, res) => {\n  res.json({ status: 'healthy' })\n})\n\n# Add to Kubernetes probes",
            severity=Severity.LOW,
            category=Category.OBSERVABILITY,
            tags=["kubernetes", "health", "probe", "monitoring"],
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

                    if not has_liveness and not has_readiness:
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=self.rule.severity,
                            category=self.rule.category,
                            description=f"Container '{container.get('name')}' has no health probes configured",
                            recommendation=self.rule.recommendation,
                            file_path=file_path,
                            resource_name=container.get("name"),
                            metadata={"container": container.get("name")},
                        ))

        return findings


@register_rule(file_types=["kubernetes", "terraform"])
class ObsMissingApplicationLogsRule(BaseRule):
    """OBS-007: Check for missing application log configuration."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="OBS-007",
            name="Missing Application Logs",
            description="Applications may not be configured for structured logging",
            recommendation="Implement structured logging:\n\n# Python\nimport logging\nlogging.basicConfig(\n  format='%(asctime)s %(levelname)s %(message)s',\n  level=logging.INFO\n)",
            severity=Severity.MEDIUM,
            category=Category.OBSERVABILITY,
            tags=["kubernetes", "logging", "structured-logging", "json"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        structured_log_indicators = [
            "json", "structured", "logrus", "zap", "zerolog",
            "winston", "bunyan", "structlog",
        ]

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") in ["Deployment", "Pod"]:
                containers = resource.get("properties", {}).get("containers", [])

                for container in containers:
                    env_vars = container.get("env", [])
                    image = container.get("image", "").lower()

                    has_structured_logging = False

                    # Check for logging libraries in image
                    if any(lib in image for lib in ["logstash", "fluent", "splunk"]):
                        has_structured_logging = True

                    # Check environment variables
                    for env in env_vars:
                        env_name = str(env.get("name", "")).lower()
                        env_value = str(env.get("value", "")).lower()
                        if "log" in env_name and any(ind in env_value for ind in structured_log_indicators):
                            has_structured_logging = True

                    if not has_structured_logging:
                        findings.append(RuleFinding(
                            rule_id=self.rule.id,
                            rule_name=self.rule.name,
                            severity=Severity.LOW,
                            category=self.rule.category,
                            description=f"Container '{container.get('name')}' may not use structured logging",
                            recommendation=self.rule.recommendation,
                            file_path=file_path,
                            resource_name=container.get("name"),
                            metadata={"container": container.get("name")},
                        ))

        return findings


@register_rule(file_types=["kubernetes", "terraform"])
class ObsMissingErrorTrackingRule(BaseRule):
    """OBS-008: Check for missing error tracking."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="OBS-0BS-008",
            name="No Error Tracking",
            description="No error tracking integration detected for exception monitoring",
            recommendation="Integrate error tracking:\n\n# Sentry\nimport * as Sentry\nSentry.init({ dsn: 'your-dsn' })\n\n# Or use: Datadog, New Relic, Rollbar",
            severity=Severity.MEDIUM,
            category=Category.OBSERVABILITY,
            tags=["kubernetes", "error-tracking", "sentry", "monitoring"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        error_tracking_indicators = [
            "sentry", "datadog", "newrelic", "rollbar",
            "bugsnag", "honeybadger", "airbrake",
            "error-tracking", "exception",
        ]

        has_error_tracking = False
        has_workload = False

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") in ["Deployment", "Pod"]:
                has_workload = True
                containers = resource.get("properties", {}).get("containers", [])

                for container in containers:
                    env_vars = container.get("env", [])
                    image = container.get("image", "").lower()

                    for env in env_vars:
                        env_name = str(env.get("name", "")).lower()
                        if any(ind in env_name for ind in error_tracking_indicators):
                            has_error_tracking = True
                            break

        if has_workload and not has_error_tracking:
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


@register_rule(file_types=["kubernetes", "terraform"])
class ObsMissingSLAMonitoringRule(BaseRule):
    """OBS-009: Check for missing SLA monitoring."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="OBS-009",
            name="No SLA Monitoring",
            description="No SLA/SLO monitoring configuration detected",
            recommendation="Configure SLA monitoring:\n\n# Define SLOs in Prometheus\n- record: slo_error_rate\n  expr: sum(rate(http_requests_total{status=~'5..'}[5m]))\n\n# Use tools like Sloth, Nobl9",
            severity=Severity.LOW,
            category=Category.OBSERVABILITY,
            tags=["kubernetes", "sla", "slo", "monitoring"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        sla_indicators = [
            "slo", "sla", "service-level", "error-budget",
            "burn-rate", "nobl9", "sloth",
        ]

        has_sla_monitoring = False
        has_service = False

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") == "Service":
                has_service = True

            name = resource.get("name", "").lower()
            if any(ind in name for ind in sla_indicators):
                has_sla_monitoring = True

        if has_service and not has_sla_monitoring:
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


@register_rule(file_types=["kubernetes", "terraform"])
class ObsMissingPerformanceMetricsRule(BaseRule):
    """OBS-010: Check for missing performance metrics."""

    @property
    def rule(self) -> Rule:
        return Rule(
            id="OBS-010",
            name="No Performance Metrics",
            description="No performance metrics collection configured for latency and throughput",
            recommendation="Configure performance metrics:\n\n# Add custom metrics\nfrom prometheus_client import Histogram\nREQUEST_LATENCY = Histogram('request_latency_seconds')",
            severity=Severity.MEDIUM,
            category=Category.OBSERVABILITY,
            tags=["kubernetes", "performance", "metrics", "latency"],
        )

    def evaluate(self, resources: list[dict[str, Any]], file_path: str) -> list[RuleFinding]:
        findings = []
        performance_indicators = [
            "latency", "throughput", "request_duration", "response_time",
            "performance", "histogram", "summary",
        ]

        has_performance_metrics = False
        has_workload = False

        for resource in resources:
            if resource.get("file_type") != "kubernetes":
                continue

            if resource.get("kind") in ["Deployment", "Pod"]:
                has_workload = True
                containers = resource.get("properties", {}).get("containers", [])

                for container in containers:
                    env_vars = container.get("env", [])
                    for env in env_vars:
                        env_name = str(env.get("name", "")).lower()
                        if any(ind in env_name for ind in performance_indicators):
                            has_performance_metrics = True
                            break

        if has_workload and not has_performance_metrics:
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
