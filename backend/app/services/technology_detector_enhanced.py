"""
Production-Grade Technology Detector with Categorization

Detects and categorizes technologies into:
- Cloud (AWS, Azure, GCP)
- Infrastructure as Code (Terraform, Pulumi, CloudFormation)
- CI/CD (GitHub Actions, Jenkins, GitLab CI, etc.)
- Containers (Docker, Kubernetes, Helm)
- Monitoring (Prometheus, Grafana, etc.)
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TechnologyInfo:
    """Information about a detected technology."""
    name: str
    category: str
    subcategory: str | None = None
    confidence: float = 0.95
    files: list[str] = field(default_factory=list)
    cloud_provider: str | None = None  # For IaC tools

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "category": self.category,
            "subcategory": self.subcategory,
            "confidence": self.confidence,
            "files_count": len(self.files),
            "sample_files": self.files[:3],  # First 3 files for tooltip
            "cloud_provider": self.cloud_provider,
        }


@dataclass
class TechnologyDetection:
    """Complete technology detection result."""
    technologies: list[TechnologyInfo] = field(default_factory=list)

    def get_by_category(self, category: str) -> list[TechnologyInfo]:
        """Get technologies by category."""
        return [t for t in self.technologies if t.category == category]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        # Group by category
        categories = {}
        for tech in self.technologies:
            if tech.category not in categories:
                categories[tech.category] = []
            categories[tech.category].append(tech.to_dict())

        return {
            "technologies": [tech.to_dict() for tech in self.technologies],
            "by_category": categories,
            "summary": {
                "total": len(self.technologies),
                "cloud": len(self.get_by_category("cloud")),
                "iac": len(self.get_by_category("iac")),
                "cicd": len(self.get_by_category("cicd")),
                "containers": len(self.get_by_category("containers")),
                "monitoring": len(self.get_by_category("monitoring")),
            }
        }


def detect_technologies_enhanced(files: list[str]) -> TechnologyDetection:
    """
    Enhanced technology detection with categorization.
    
    Args:
        files: List of file paths in repository
        
    Returns:
        TechnologyDetection with categorized technologies
    """
    detection = TechnologyDetection()

    # Track what we've found
    found_techs = {}

    for file_path in files:
        file_name = file_path.split("/")[-1].lower()
        file_lower = file_path.lower()

        # === CLOUD PROVIDERS ===

        # AWS
        if _is_aws_file(file_path, file_name):
            if 'aws' not in found_techs:
                found_techs['aws'] = TechnologyInfo(
                    name="aws",
                    category="cloud",
                    subcategory="Amazon Web Services",
                    confidence=0.95,
                    cloud_provider="aws"
                )
            found_techs['aws'].files.append(file_path)

        # Azure
        if _is_azure_file(file_path, file_name):
            if 'azure' not in found_techs:
                found_techs['azure'] = TechnologyInfo(
                    name="azure",
                    category="cloud",
                    subcategory="Microsoft Azure",
                    confidence=0.95,
                    cloud_provider="azure"
                )
            found_techs['azure'].files.append(file_path)

        # GCP
        if _is_gcp_file(file_path, file_name):
            if 'gcp' not in found_techs:
                found_techs['gcp'] = TechnologyInfo(
                    name="gcp",
                    category="cloud",
                    subcategory="Google Cloud Platform",
                    confidence=0.95,
                    cloud_provider="gcp"
                )
            found_techs['gcp'].files.append(file_path)

        # === INFRASTRUCTURE AS CODE ===

        # Terraform
        if file_path.endswith((".tf", ".tf.json", ".tfvars")):
            if 'terraform' not in found_techs:
                # Detect cloud provider from file content hints
                cloud = _detect_terraform_cloud_provider(file_path, file_name)
                found_techs['terraform'] = TechnologyInfo(
                    name="terraform",
                    category="iac",
                    subcategory="Infrastructure as Code",
                    confidence=0.98,
                    cloud_provider=cloud
                )
            found_techs['terraform'].files.append(file_path)

        # Pulumi
        if "pulumi" in file_path or file_name in ["pulumi.yaml", "pulumi.dev.yaml", "pulumi.prod.yaml"]:
            if 'pulumi' not in found_techs:
                found_techs['pulumi'] = TechnologyInfo(
                    name="pulumi",
                    category="iac",
                    subcategory="Infrastructure as Code",
                    confidence=0.95
                )
            found_techs['pulumi'].files.append(file_path)

        # CloudFormation
        if "cloudformation" in file_path or file_name.startswith("cloudformation"):
            if 'cloudformation' not in found_techs:
                found_techs['cloudformation'] = TechnologyInfo(
                    name="cloudformation",
                    category="iac",
                    subcategory="AWS CloudFormation",
                    confidence=0.90,
                    cloud_provider="aws"
                )
            found_techs['cloudformation'].files.append(file_path)

        # === CI/CD ===

        # GitHub Actions
        if ".github/workflows/" in file_path and file_path.endswith((".yml", ".yaml")):
            if 'github_actions' not in found_techs:
                found_techs['github_actions'] = TechnologyInfo(
                    name="github_actions",
                    category="cicd",
                    subcategory="GitHub Actions",
                    confidence=0.98
                )
            found_techs['github_actions'].files.append(file_path)

        # GitLab CI
        if file_name == ".gitlab-ci.yml" or ".gitlab-ci.yml" in file_path:
            if 'gitlab_ci' not in found_techs:
                found_techs['gitlab_ci'] = TechnologyInfo(
                    name="gitlab_ci",
                    category="cicd",
                    subcategory="GitLab CI/CD",
                    confidence=0.98
                )
            found_techs['gitlab_ci'].files.append(file_path)

        # Jenkins
        if file_name.lower() == "jenkinsfile" or "jenkins" in file_path.lower():
            if 'jenkins' not in found_techs:
                found_techs['jenkins'] = TechnologyInfo(
                    name="jenkins",
                    category="cicd",
                    subcategory="Jenkins CI/CD",
                    confidence=0.95
                )
            found_techs['jenkins'].files.append(file_path)

        # CircleCI
        if ".circleci/" in file_path or file_name == "circle.yml":
            if 'circleci' not in found_techs:
                found_techs['circleci'] = TechnologyInfo(
                    name="circleci",
                    category="cicd",
                    subcategory="CircleCI",
                    confidence=0.95
                )
            found_techs['circleci'].files.append(file_path)

        # Azure DevOps
        if "azure-pipelines" in file_path or file_name == "azure-pipelines.yml":
            if 'azure_devops' not in found_techs:
                found_techs['azure_devops'] = TechnologyInfo(
                    name="azure_devops",
                    category="cicd",
                    subcategory="Azure DevOps Pipelines",
                    confidence=0.95,
                    cloud_provider="azure"
                )
            found_techs['azure_devops'].files.append(file_path)

        # === CONTAINERS ===

        # Docker
        if file_name in ["dockerfile", "containerfile"] or "dockerfile" in file_name:
            if 'docker' not in found_techs:
                found_techs['docker'] = TechnologyInfo(
                    name="docker",
                    category="containers",
                    subcategory="Containerization",
                    confidence=0.98
                )
            found_techs['docker'].files.append(file_path)

        # Docker Compose
        if file_name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
            if 'docker_compose' not in found_techs:
                found_techs['docker_compose'] = TechnologyInfo(
                    name="docker_compose",
                    category="containers",
                    subcategory="Docker Compose",
                    confidence=0.98
                )
            found_techs['docker_compose'].files.append(file_path)

        # Kubernetes
        if _is_kubernetes_file(file_path, file_name):
            if 'kubernetes' not in found_techs:
                # Try to detect managed K8s variant
                k8s_variant = _detect_kubernetes_variant(file_path, file_name)
                found_techs['kubernetes'] = TechnologyInfo(
                    name="kubernetes",
                    category="containers",
                    subcategory=k8s_variant or "Kubernetes",
                    confidence=0.95
                )
            found_techs['kubernetes'].files.append(file_path)

        # Helm
        if ("chart.yaml" in file_name or "values.yaml" in file_name) and ("charts/" in file_path or "helm/" in file_path):
            if 'helm' not in found_techs:
                found_techs['helm'] = TechnologyInfo(
                    name="helm",
                    category="containers",
                    subcategory="Kubernetes Package Manager",
                    confidence=0.95
                )
            found_techs['helm'].files.append(file_path)

        # === MONITORING ===

        # Prometheus
        if "prometheus" in file_path or "alertmanager" in file_path or "promtail" in file_path:
            if 'prometheus' not in found_techs:
                found_techs['prometheus'] = TechnologyInfo(
                    name="prometheus",
                    category="monitoring",
                    subcategory="Metrics & Monitoring",
                    confidence=0.95
                )
            found_techs['prometheus'].files.append(file_path)

        # Grafana
        if "grafana" in file_path:
            if 'grafana' not in found_techs:
                found_techs['grafana'] = TechnologyInfo(
                    name="grafana",
                    category="monitoring",
                    subcategory="Visualization & Dashboards",
                    confidence=0.95
                )
            found_techs['grafana'].files.append(file_path)

        # ELK Stack
        if "elasticsearch" in file_path or "logstash" in file_path or "kibana" in file_path:
            if 'elk' not in found_techs:
                found_techs['elk'] = TechnologyInfo(
                    name="elk_stack",
                    category="monitoring",
                    subcategory="Logging & Analytics",
                    confidence=0.90
                )
            found_techs['elk'].files.append(file_path)

        # === CONFIGURATION MANAGEMENT ===

        # Ansible
        if ("ansible" in file_path or "playbook" in file_path) and file_path.endswith((".yml", ".yaml")):
            if 'ansible' not in found_techs:
                found_techs['ansible'] = TechnologyInfo(
                    name="ansible",
                    category="config_management",
                    subcategory="Configuration Management",
                    confidence=0.95
                )
            found_techs['ansible'].files.append(file_path)

    # Convert to list
    detection.technologies = list(found_techs.values())

    return detection


# === Helper Functions ===

def _is_aws_file(file_path: str, file_name: str) -> bool:
    """Check if file is related to AWS."""
    aws_indicators = [
        'aws', 'amazon', '.aws', 'ec2', 's3', 'lambda', 'cloudformation',
        'iam', 'vpc', 'rds', 'eks', 'ecs', 'dynamodb', 'sqs', 'sns',
        'cloudwatch', 'cloudfront', 'route53', 'elastic'
    ]
    return any(ind in file_path.lower() for ind in aws_indicators)


def _is_azure_file(file_path: str, file_name: str) -> bool:
    """Check if file is related to Azure."""
    azure_indicators = [
        'azure', 'microsoft', '.azure', 'aks', 'arm', 'bicep',
        'app service', 'function app', 'cosmos', 'blob storage',
        'azure devops', 'azure ad', 'key vault', 'service bus'
    ]
    return any(ind in file_path.lower() for ind in azure_indicators)


def _is_gcp_file(file_path: str, file_name: str) -> bool:
    """Check if file is related to GCP."""
    gcp_indicators = [
        'gcp', 'google', '.gcp', 'gke', 'bigquery', 'cloud functions',
        'cloud run', 'gcs', 'pubsub', 'cloud sql'
    ]
    return any(ind in file_path.lower() for ind in gcp_indicators)


def _detect_terraform_cloud_provider(file_path: str, file_name: str) -> str | None:
    """Detect which cloud provider Terraform is targeting."""
    file_lower = file_path.lower()

    if _is_aws_file(file_path, file_name):
        return "aws"
    elif _is_azure_file(file_path, file_name):
        return "azure"
    elif _is_gcp_file(file_path, file_name):
        return "gcp"

    return None


def _is_kubernetes_file(file_path: str, file_name: str) -> bool:
    """Check if file is a Kubernetes manifest."""
    if not file_path.endswith((".yaml", ".yml")):
        return False

    # Check directory indicators
    k8s_indicators = ["kubernetes", "k8s", "manifests", "deployments", "helm", "charts"]
    if any(ind in file_path.lower() for ind in k8s_indicators):
        return True

    # Check file name patterns
    k8s_patterns = ["deployment", "service", "pod", "configmap", "secret", "ingress", "namespace"]
    if any(pattern in file_name for pattern in k8s_patterns):
        return True

    return False


def _detect_kubernetes_variant(file_path: str, file_name: str) -> str | None:
    """Try to detect managed Kubernetes variant (EKS, AKS, GKE)."""
    file_lower = file_path.lower()

    if "eks" in file_lower or "amazon" in file_lower or "aws" in file_lower:
        return "Amazon EKS"
    elif "aks" in file_lower or "azure" in file_lower:
        return "Azure AKS"
    elif "gke" in file_lower or "google" in file_lower:
        return "Google GKE"

    return None
