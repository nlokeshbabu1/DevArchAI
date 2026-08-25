"""
Helm Chart Security Scanner

Scans Helm charts for security and reliability issues.
Implements rules from docs/rules/azu_helm.md
"""

from pathlib import Path
from typing import Any

import yaml

from app.rules.base import RuleFinding, Severity


class HelmScanner:
    """
    Scanner for Helm charts.
    
    Detects security and reliability issues in:
    - Chart.yaml
    - values.yaml
    - templates/*.yaml
    """

    def __init__(self):
        self.findings: list[RuleFinding] = []
        self.files_scanned: list[str] = []

    def scan(self, repo_path: str, files: list[dict[str, Any]]) -> list[RuleFinding]:
        """
        Scan Helm chart files for security issues.
        
        Args:
            repo_path: Path to repository
            files: List of file dicts with path and content
            
        Returns:
            List of security findings
        """
        self.findings = []

        # Group files by Helm chart directory
        charts = self._group_by_chart(repo_path, files)

        for chart_path, chart_files in charts.items():
            self._scan_chart(chart_path, chart_files)

        return self.findings

    def _group_by_chart(self, repo_path: str, files: list[dict[str, Any]]) -> dict[str, list[dict]]:
        """Group files by Helm chart directory."""
        charts = {}

        for file_info in files:
            file_path = file_info.get("file_path", "")
            content = file_info.get("content", "")

            # Check if this is a Helm chart file
            if "Chart.yaml" in file_path or "values.yaml" in file_path or "/templates/" in file_path:
                # Find chart root (directory containing Chart.yaml)
                path_parts = Path(file_path).parts
                chart_root = None

                for i, part in enumerate(path_parts):
                    if part == "Chart.yaml":
                        chart_root = str(Path(*path_parts[:i]))
                        break

                if not chart_root:
                    # Fallback: treat the file's directory as the chart root
                    # so standalone values.yaml / template files are still scanned.
                    chart_root = str(Path(*path_parts[:-1])) or "."

                if chart_root:
                    if chart_root not in charts:
                        charts[chart_root] = []
                    charts[chart_root].append(file_info)

        return charts

    def _scan_chart(self, chart_path: str, files: list[dict[str, Any]]) -> None:
        """Scan a single Helm chart."""
        chart_yaml = None
        values_yaml = None
        templates = []
        chart_yaml_path = ""
        values_yaml_path = ""

        for file_info in files:
            file_path = file_info.get("file_path", "")
            content = file_info.get("content", "")

            if "Chart.yaml" in file_path:
                chart_yaml = self._parse_yaml(content, file_path)
                chart_yaml_path = file_path
            elif "values.yaml" in file_path:
                values_yaml = self._parse_yaml(content, file_path)
                values_yaml_path = file_path
            elif "/templates/" in file_path:
                templates.append(self._parse_yaml(content, file_path))

        # Run checks
        if chart_yaml:
            self._check_chart_yaml(chart_yaml, chart_yaml_path)

        if values_yaml:
            self._check_values_yaml(values_yaml, values_yaml_path)

        for template in templates:
            if template:
                self._check_templates(template)

    def _parse_yaml(self, content: str, file_path: str) -> dict | None:
        """Parse YAML content safely."""
        try:
            # Handle Helm templates (ignore {{ }} blocks)
            import re
            # Replace Helm template expressions with empty strings for YAML parsing
            cleaned = re.sub(r'\{\{.*?\}\}', '', content, flags=re.DOTALL)
            # Remove lines that are only template expressions
            lines = [line for line in cleaned.split('\n') if line.strip() and not line.strip().startswith('---')]
            cleaned = '\n'.join(lines)
            result = yaml.safe_load(cleaned)
            # Add file_path annotation for template findings
            if result and isinstance(result, dict):
                result.setdefault('metadata', {})['annotations'] = {'file_path': file_path}
            return result or {}
        except Exception:
            return None

    def _check_chart_yaml(self, chart: dict, file_path: str) -> None:
        """Check Chart.yaml for issues."""
        # HELM-VER-001: Unpinned dependencies
        dependencies = chart.get("dependencies", [])
        for dep in dependencies:
            version = dep.get("version", "")
            if version == "*" or version == "latest":
                self.findings.append(RuleFinding(
                    rule_id="HELM-VER-001",
                    rule_name="Chart Dependency Version Not Pinned",
                    severity=Severity.LOW,
                    category="reliability",
                    description=f"Dependency '{dep.get('name')}' uses unpinned version '{version}'",
                    recommendation="Pin dependency to specific version (e.g., 1.2.3)",
                    file_path=file_path,
                    resource_name=dep.get("name", "unknown"),
                    confidence=0.9,
                ))

    def _check_values_yaml(self, values: dict, file_path: str) -> None:
        """Check values.yaml for security issues."""
        # HELM-SEC-001: Running as root
        security_context = values.get("securityContext", {})
        if security_context.get("runAsRoot") or security_context.get("runAsUser") == 0:
            self.findings.append(RuleFinding(
                rule_id="HELM-SEC-001",
                rule_name="Container Running as Root",
                severity=Severity.CRITICAL,
                category="security",
                description="Container is configured to run as root user",
                recommendation="Set runAsNonRoot: true and runAsUser: 1000",
                file_path=file_path,
                resource_name="securityContext",
                confidence=0.95,
            ))

        # HELM-SEC-002: Privileged container
        if security_context.get("privileged"):
            self.findings.append(RuleFinding(
                rule_id="HELM-SEC-002",
                rule_name="Privileged Container",
                severity=Severity.CRITICAL,
                category="security",
                description="Container runs in privileged mode",
                recommendation="Set privileged: false",
                file_path=file_path,
                resource_name="securityContext",
                confidence=1.0,
            ))

        # HELM-REL-001: Missing resource limits
        resources = values.get("resources", {})
        if not resources or resources == {}:
            self.findings.append(RuleFinding(
                rule_id="HELM-REL-001",
                rule_name="Missing Resource Limits",
                severity=Severity.HIGH,
                category="reliability",
                description="Container has no resource limits defined",
                recommendation="Define CPU and memory limits/requests",
                file_path=file_path,
                resource_name="resources",
                confidence=0.9,
            ))
        else:
            limits = resources.get("limits", {})
            if not limits.get("cpu") or not limits.get("memory"):
                self.findings.append(RuleFinding(
                    rule_id="HELM-REL-001",
                    rule_name="Incomplete Resource Limits",
                    severity=Severity.HIGH,
                    category="reliability",
                    description="Container resource limits are incomplete",
                    recommendation="Define both CPU and memory limits",
                    file_path=file_path,
                    resource_name="resources",
                    confidence=0.85,
                ))

        # HELM-REL-002: Missing probes
        liveness_probe = values.get("livenessProbe", {})
        readiness_probe = values.get("readinessProbe", {})

        if not liveness_probe or liveness_probe == {}:
            self.findings.append(RuleFinding(
                rule_id="HELM-REL-002",
                rule_name="Missing Liveness Probe",
                severity=Severity.MEDIUM,
                category="reliability",
                description="Container has no liveness probe configured",
                recommendation="Define livenessProbe with httpGet or exec",
                file_path=file_path,
                resource_name="livenessProbe",
                confidence=0.9,
            ))

        if not readiness_probe or readiness_probe == {}:
            self.findings.append(RuleFinding(
                rule_id="HELM-REL-002",
                rule_name="Missing Readiness Probe",
                severity=Severity.MEDIUM,
                category="reliability",
                description="Container has no readiness probe configured",
                recommendation="Define readinessProbe with httpGet or exec",
                file_path=file_path,
                resource_name="readinessProbe",
                confidence=0.9,
            ))

        # HELM-REL-003: Single replica
        replica_count = values.get("replicaCount", 1)
        if replica_count == 1:
            self.findings.append(RuleFinding(
                rule_id="HELM-REL-003",
                rule_name="Single Replica Deployment",
                severity=Severity.MEDIUM,
                category="reliability",
                description="Deployment has only 1 replica, reducing availability",
                recommendation="Set replicaCount to 2 or more for production",
                file_path=file_path,
                resource_name="replicaCount",
                confidence=0.8,
            ))

        # HELM-IMG-001: Image tag not pinned
        image = values.get("image", {})
        tag = image.get("tag", "")
        if tag == "latest" or not tag:
            self.findings.append(RuleFinding(
                rule_id="HELM-IMG-001",
                rule_name="Image Tag Not Pinned",
                severity=Severity.HIGH,
                category="security",
                description=f"Container image uses '{tag or 'no tag'}' tag",
                recommendation="Use specific version tag (e.g., v1.2.3)",
                file_path=file_path,
                resource_name=image.get("repository", "unknown"),
                confidence=0.95,
            ))

    def _check_templates(self, template: dict) -> None:
        """Check Kubernetes templates for security issues."""
        if not template or not isinstance(template, dict):
            return

        kind = template.get("kind", "")

        # Check Deployments
        if kind == "Deployment":
            self._check_deployment(template)

    def _check_deployment(self, deployment: dict) -> None:
        """Check Deployment template for security issues."""
        spec = deployment.get("spec", {})
        template_spec = spec.get("template", {}).get("spec", {})

        # Check pod security context
        pod_security = template_spec.get("securityContext", {})
        if not pod_security.get("runAsNonRoot"):
            # Already reported in values.yaml check
            pass

        # Check containers
        containers = template_spec.get("containers", [])
        for container in containers:
            container_security = container.get("securityContext", {})

            # HELM-SEC-002: Privilege escalation
            if container_security.get("allowPrivilegeEscalation"):
                file_path = deployment.get("metadata", {}).get("annotations", {}).get("file_path", "unknown")
                self.findings.append(RuleFinding(
                    rule_id="HELM-SEC-002",
                    rule_name="Privilege Escalation Allowed",
                    severity=Severity.CRITICAL,
                    category="security",
                    description=f"Container '{container.get('name')}' allows privilege escalation",
                    recommendation="Set allowPrivilegeEscalation: false",
                    file_path=file_path,
                    resource_name=container.get("name", "unknown"),
                    confidence=0.95,
                ))
