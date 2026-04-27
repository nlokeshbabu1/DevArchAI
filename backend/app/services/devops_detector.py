"""
DevOps Detector Service
Analyzes repository files to detect DevOps tools and configurations.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class DevOpsStackResult:
    """Result of DevOps stack detection."""

    # Containers
    docker: bool = False
    docker_files: list[str] = field(default_factory=list)

    # Infrastructure as Code
    terraform: bool = False
    terraform_files: list[str] = field(default_factory=list)
    pulumi: bool = False
    pulumi_files: list[str] = field(default_factory=list)
    cloudformation: bool = False
    cloudformation_files: list[str] = field(default_factory=list)
    ansible: bool = False
    ansible_files: list[str] = field(default_factory=list)

    # Kubernetes
    kubernetes: bool = False
    kubernetes_files: list[str] = field(default_factory=list)
    helm: bool = False
    helm_files: list[str] = field(default_factory=list)
    kustomize: bool = False
    kustomize_files: list[str] = field(default_factory=list)

    # CI/CD
    cicd: Optional[str] = None  # github_actions, gitlab_ci, jenkins, circleci, travis, azure_devops
    cicd_files: list[str] = field(default_factory=list)

    # Monitoring
    monitoring: bool = False
    monitoring_files: list[str] = field(default_factory=list)
    prometheus: bool = False
    prometheus_files: list[str] = field(default_factory=list)
    grafana: bool = False
    grafana_files: list[str] = field(default_factory=list)
    datadog: bool = False
    datadog_files: list[str] = field(default_factory=list)

    # Service Mesh
    service_mesh: bool = False
    service_mesh_files: list[str] = field(default_factory=list)
    istio: bool = False
    istio_files: list[str] = field(default_factory=list)

    # Security
    security_scanning: bool = False
    security_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "docker": self.docker,
            "docker_files": self.docker_files,
            "terraform": self.terraform,
            "terraform_files": self.terraform_files,
            "pulumi": self.pulumi,
            "pulumi_files": self.pulumi_files,
            "cloudformation": self.cloudformation,
            "cloudformation_files": self.cloudformation_files,
            "ansible": self.ansible,
            "ansible_files": self.ansible_files,
            "kubernetes": self.kubernetes,
            "kubernetes_files": self.kubernetes_files,
            "helm": self.helm,
            "helm_files": self.helm_files,
            "kustomize": self.kustomize,
            "kustomize_files": self.kustomize_files,
            "cicd": self.cicd,
            "cicd_files": self.cicd_files,
            "monitoring": self.monitoring,
            "monitoring_files": self.monitoring_files,
            "prometheus": self.prometheus,
            "prometheus_files": self.prometheus_files,
            "grafana": self.grafana,
            "grafana_files": self.grafana_files,
            "datadog": self.datadog,
            "datadog_files": self.datadog_files,
            "service_mesh": self.service_mesh,
            "service_mesh_files": self.service_mesh_files,
            "istio": self.istio,
            "istio_files": self.istio_files,
            "security_scanning": self.security_scanning,
            "security_files": self.security_files,
        }


class DevOpsDetector:
    """Service for detecting DevOps tools and configurations in a repository."""

    # File patterns for detection
    DOCKER_PATTERNS = [
        "Dockerfile",
        "Dockerfile.dev",
        "Dockerfile.prod",
        "docker-compose.yml",
        "docker-compose.yaml",
        "docker-compose.override.yml",
        "Containerfile",
    ]

    TERRAFORM_PATTERNS = [
        ".tf",  # Extension
        ".tfvars",
        ".tf.json",
    ]

    PULUMI_PATTERNS = [
        "Pulumi.yaml",
        "Pulumi.dev.yaml",
        "Pulumi.prod.yaml",
    ]

    CLOUDFORMATION_PATTERNS = [
        "cloudformation.yml",
        "cloudformation.yaml",
        "cloudformation.json",
        ".template",
    ]

    ANSIBLE_PATTERNS = [
        "ansible.cfg",
        "inventory",
        "hosts",
        ".yml",  # Ansible playbooks (checked with directory)
    ]

    KUBERNETES_PATTERNS = [
        ".yaml",  # Kubernetes manifests (checked with directory)
        ".yml",
    ]

    KUBERNETES_DIRS = [
        "k8s/",
        "kubernetes/",
        "k8s-manifests/",
        "manifests/",
        "deployments/",
        ".kube/",
    ]

    HELM_PATTERNS = [
        "Chart.yaml",
        "values.yaml",
        "Chart.lock",
    ]

    KUSTOMIZE_PATTERNS = [
        "kustomization.yaml",
        "kustomization.yml",
        "Kustomization",
    ]

    # CI/CD patterns
    GITHUB_ACTIONS_DIRS = [".github/workflows/"]
    GITLAB_CI_FILES = [".gitlab-ci.yml", ".gitlab-ci.yaml"]
    JENKINS_FILES = ["Jenkinsfile", "Jenkinsfile.prod", "Jenkinsfile.dev"]
    CIRCLECI_FILES = ["circle.yml", ".circleci/config.yml"]
    TRAVIS_FILES = [".travis.yml"]
    AZURE_DEVOPS_FILES = ["azure-pipelines.yml", "azure-pipelines.yaml"]
    DRONE_FILES = [".drone.yml"]
    ARGOCD_FILES = ["application.yml", "applicationset.yml"]

    # Monitoring patterns
    PROMETHEUS_FILES = [
        "prometheus.yml",
        "prometheus.yaml",
        "prometheus.rules.yml",
        "alertmanager.yml",
    ]

    GRAFANA_PATTERNS = [
        "grafana/",
        "dashboards/",
        ".dashboard.json",
        ".dashboard.yml",
    ]

    DATADOG_FILES = [
        "datadog.yaml",
        "datadog.yml",
        "conf.d/",
    ]

    # Service mesh patterns
    ISTIO_PATTERNS = [
        "istio-system/",
        "istio-",
        "virtualservice",
        "destinationrule",
        ".istio.",
    ]

    LINKERD_PATTERNS = [
        "linkerd/",
        ".linkerd.",
    ]

    # Security scanning patterns
    SECURITY_FILES = [
        ".trivyignore",
        ".hadolint.yaml",
        ".yamllint",
        ".checkov.yaml",
        "tfsec.yaml",
        ".tfsec/",
        "snyk.yaml",
        ".sonarqube/",
        "sonar-project.properties",
    ]

    def detect(self, files: list[str]) -> DevOpsStackResult:
        """
        Detect DevOps tools and configurations from a list of files.

        Args:
            files: List of file paths in the repository

        Returns:
            DevOpsStackResult with detected tools and files
        """
        result = DevOpsStackResult()

        for file_path in files:
            self._detect_docker(file_path, result)
            self._detect_terraform(file_path, result)
            self._detect_pulumi(file_path, result)
            self._detect_cloudformation(file_path, result)
            self._detect_ansible(file_path, result)
            self._detect_kubernetes(file_path, result)
            self._detect_helm(file_path, result)
            self._detect_kustomize(file_path, result)
            self._detect_cicd(file_path, result)
            self._detect_monitoring(file_path, result)
            self._detect_service_mesh(file_path, result)
            self._detect_security(file_path, result)

        # Set aggregate flags
        result.monitoring = result.prometheus or result.grafana or result.datadog
        result.service_mesh = result.istio or bool(result.istio_files)

        # Determine primary CI/CD
        self._determine_primary_cicd(result)

        logger.info(
            "DevOps stack detection completed",
            docker=result.docker,
            terraform=result.terraform,
            kubernetes=result.kubernetes,
            cicd=result.cicd,
            monitoring=result.monitoring,
        )

        return result

    def _detect_docker(self, file_path: str, result: DevOpsStackResult) -> None:
        """Detect Docker files."""
        file_name = file_path.split("/")[-1]

        if file_name in self.DOCKER_PATTERNS or file_name.startswith("Dockerfile"):
            result.docker = True
            result.docker_files.append(file_path)

    def _detect_terraform(self, file_path: str, result: DevOpsStackResult) -> None:
        """Detect Terraform files."""
        if any(file_path.endswith(ext) for ext in self.TERRAFORM_PATTERNS):
            result.terraform = True
            result.terraform_files.append(file_path)

    def _detect_pulumi(self, file_path: str, result: DevOpsStackResult) -> None:
        """Detect Pulumi files."""
        file_name = file_path.split("/")[-1]

        if file_name in self.PULUMI_PATTERNS:
            result.pulumi = True
            result.pulumi_files.append(file_path)

    def _detect_cloudformation(self, file_path: str, result: DevOpsStackResult) -> None:
        """Detect CloudFormation files."""
        file_name = file_path.lower()

        if any(pattern in file_name for pattern in self.CLOUDFORMATION_PATTERNS):
            result.cloudformation = True
            result.cloudformation_files.append(file_path)

    def _detect_ansible(self, file_path: str, result: DevOpsStackResult) -> None:
        """Detect Ansible files."""
        file_name = file_path.split("/")[-1]
        dir_name = file_path.split("/")[0] if "/" in file_path else ""

        if file_name in self.ANSIBLE_PATTERNS:
            result.ansible = True
            result.ansible_files.append(file_path)
        elif file_name.endswith(".yml") or file_name.endswith(".yaml"):
            # Check if in ansible directory
            if "ansible/" in file_path or "playbooks/" in file_path or "roles/" in file_path:
                result.ansible = True
                result.ansible_files.append(file_path)

    def _detect_kubernetes(self, file_path: str, result: DevOpsStackResult) -> None:
        """Detect Kubernetes files."""
        file_name = file_path.split("/")[-1]

        # Check if in k8s directory
        for k8s_dir in self.KUBERNETES_DIRS:
            if file_path.startswith(k8s_dir) or f"/{k8s_dir}" in file_path:
                if file_name.endswith(".yaml") or file_name.endswith(".yml"):
                    result.kubernetes = True
                    result.kubernetes_files.append(file_path)
                    return

        # Check for k8s keywords in filename
        k8s_keywords = ["deployment", "service", "ingress", "configmap", "secret", "pod", "namespace", "statefulset", "daemonset"]
        if any(keyword in file_name.lower() for keyword in k8s_keywords):
            if file_name.endswith(".yaml") or file_name.endswith(".yml"):
                result.kubernetes = True
                result.kubernetes_files.append(file_path)

    def _detect_helm(self, file_path: str, result: DevOpsStackResult) -> None:
        """Detect Helm charts."""
        file_name = file_path.split("/")[-1]

        if file_name in self.HELM_PATTERNS:
            result.helm = True
            result.helm_files.append(file_path)
        elif "helm/" in file_path or "charts/" in file_path:
            if file_name.endswith(".yaml") or file_name.endswith(".yml"):
                result.helm = True
                result.helm_files.append(file_path)

    def _detect_kustomize(self, file_path: str, result: DevOpsStackResult) -> None:
        """Detect Kustomize files."""
        file_name = file_path.split("/")[-1]

        if file_name in self.KUSTOMIZE_PATTERNS:
            result.kustomize = True
            result.kustomize_files.append(file_path)

    def _detect_cicd(self, file_path: str, result: DevOpsStackResult) -> None:
        """Detect CI/CD configuration."""
        # GitHub Actions
        for dir_pattern in self.GITHUB_ACTIONS_DIRS:
            if file_path.startswith(dir_pattern):
                result.cicd_files.append(file_path)
                if result.cicd is None:
                    result.cicd = "github_actions"
                return

        # GitLab CI
        if file_path in self.GITLAB_CI_FILES:
            result.cicd_files.append(file_path)
            if result.cicd is None:
                result.cicd = "gitlab_ci"
            return

        # Jenkins
        file_name_lower = file_path.split("/")[-1].lower()
        if file_name_lower == "jenkinsfile" or file_name_lower.startswith("jenkinsfile-") or file_name_lower.startswith("jenkinsfile."):
            result.cicd_files.append(file_path)
            if result.cicd is None:
                result.cicd = "jenkins"
            return

        # CircleCI
        if file_path in self.CIRCLECI_FILES or file_path.startswith(".circleci/"):
            result.cicd_files.append(file_path)
            if result.cicd is None:
                result.cicd = "circleci"
            return

        # Travis CI
        if file_path in self.TRAVIS_FILES:
            result.cicd_files.append(file_path)
            if result.cicd is None:
                result.cicd = "travis"
            return

        # Azure DevOps
        if file_path in self.AZURE_DEVOPS_FILES:
            result.cicd_files.append(file_path)
            if result.cicd is None:
                result.cicd = "azure_devops"
            return

        # Drone CI
        if file_path in self.DRONE_FILES:
            result.cicd_files.append(file_path)
            if result.cicd is None:
                result.cicd = "drone"
            return

    def _detect_monitoring(self, file_path: str, result: DevOpsStackResult) -> None:
        """Detect monitoring configuration."""
        file_name = file_path.split("/")[-1]

        # Prometheus
        if file_name in self.PROMETHEUS_FILES:
            result.prometheus = True
            result.prometheus_files.append(file_path)
            result.monitoring_files.append(file_path)
            return

        # Grafana
        for pattern in self.GRAFANA_PATTERNS:
            if pattern in file_path.lower():
                result.grafana = True
                result.grafana_files.append(file_path)
                result.monitoring_files.append(file_path)
                return

        # Datadog
        if file_name in self.DATADOG_FILES or "datadog/" in file_path:
            result.datadog = True
            result.datadog_files.append(file_path)
            result.monitoring_files.append(file_path)

    def _detect_service_mesh(self, file_path: str, result: DevOpsStackResult) -> None:
        """Detect service mesh configuration."""
        file_lower = file_path.lower()

        # Istio
        for pattern in self.ISTIO_PATTERNS:
            if pattern in file_lower:
                result.istio = True
                result.istio_files.append(file_path)
                result.service_mesh_files.append(file_path)
                return

        # Linkerd
        for pattern in self.LINKERD_PATTERNS:
            if pattern in file_lower:
                result.service_mesh = True
                result.service_mesh_files.append(file_path)

    def _detect_security(self, file_path: str, result: DevOpsStackResult) -> None:
        """Detect security scanning configuration."""
        file_name = file_path.split("/")[-1]

        if file_name in self.SECURITY_FILES:
            result.security_scanning = True
            result.security_files.append(file_path)
            return

        # Check for security directories
        security_dirs = ["security/", ".security/", "sast/", "dast/"]
        for dir_pattern in security_dirs:
            if file_path.startswith(dir_pattern):
                result.security_scanning = True
                result.security_files.append(file_path)
                return

    def _determine_primary_cicd(self, result: DevOpsStackResult) -> None:
        """Determine the primary CI/CD tool if multiple are detected."""
        # Priority order for CI/CD tools
        priority = [
            "github_actions",
            "gitlab_ci",
            "jenkins",
            "circleci",
            "azure_devops",
            "travis",
            "drone",
        ]

        if result.cicd:
            return

        # Check files for priority-based detection
        detected = set()
        for file_path in result.cicd_files:
            if ".github/workflows/" in file_path:
                detected.add("github_actions")
            elif ".gitlab-ci" in file_path:
                detected.add("gitlab_ci")
            elif "Jenkinsfile" in file_path:
                detected.add("jenkins")
            elif ".circleci/" in file_path:
                detected.add("circleci")
            elif "azure-pipelines" in file_path:
                detected.add("azure_devops")
            elif ".travis" in file_path:
                detected.add("travis")
            elif ".drone" in file_path:
                detected.add("drone")

        # Set highest priority CI/CD
        for cicd_tool in priority:
            if cicd_tool in detected:
                result.cicd = cicd_tool
                break


# Convenience function
_detector = DevOpsDetector()


def detect_devops_stack(files: list[str]) -> DevOpsStackResult:
    """
    Detect DevOps stack from a list of repository files.

    Args:
        files: List of file paths in the repository

    Returns:
        DevOpsStackResult with detected tools
    """
    return _detector.detect(files)
