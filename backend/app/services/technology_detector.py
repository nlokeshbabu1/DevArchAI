"""
Enhanced DevOps Detector with Stack-based Scanner Configuration
Production-grade technology detection for all DevOps file types.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TechnologyStack:
    """Detected technology stack for dynamic scanner execution."""

    # Core technologies
    has_docker: bool = False
    docker_files: list[str] = field(default_factory=list)

    has_terraform: bool = False
    terraform_files: list[str] = field(default_factory=list)

    has_kubernetes: bool = False
    kubernetes_files: list[str] = field(default_factory=list)

    has_github_actions: bool = False
    github_actions_files: list[str] = field(default_factory=list)

    has_gitlab_ci: bool = False
    gitlab_ci_files: list[str] = field(default_factory=list)

    has_jenkins: bool = False
    jenkins_files: list[str] = field(default_factory=list)

    has_docker_compose: bool = False
    docker_compose_files: list[str] = field(default_factory=list)

    # Additional technologies
    has_helm: bool = False
    helm_files: list[str] = field(default_factory=list)

    has_ansible: bool = False
    ansible_files: list[str] = field(default_factory=list)

    has_circleci: bool = False
    circleci_files: list[str] = field(default_factory=list)

    has_azure_devops: bool = False
    azure_devops_files: list[str] = field(default_factory=list)

    has_travis: bool = False
    travis_files: list[str] = field(default_factory=list)

    has_drone: bool = False
    drone_files: list[str] = field(default_factory=list)

    def get_detected_technologies(self) -> list[str]:
        """Get list of detected technology names."""
        technologies = []

        if self.has_docker:
            technologies.append("docker")
        if self.has_terraform:
            technologies.append("terraform")
        if self.has_kubernetes:
            technologies.append("kubernetes")
        if self.has_github_actions:
            technologies.append("github_actions")
        if self.has_gitlab_ci:
            technologies.append("gitlab_ci")
        if self.has_jenkins:
            technologies.append("jenkins")
        if self.has_docker_compose:
            technologies.append("docker_compose")
        if self.has_helm:
            technologies.append("helm")
        if self.has_ansible:
            technologies.append("ansible")
        if self.has_circleci:
            technologies.append("circleci")
        if self.has_azure_devops:
            technologies.append("azure_devops")
        if self.has_travis:
            technologies.append("travis")
        if self.has_drone:
            technologies.append("drone")

        return technologies

    def get_scanners_to_run(self) -> list[str]:
        """Get list of scanners that should be executed."""
        scanners = []

        if self.has_terraform:
            scanners.append("terraform")
        if self.has_docker or self.has_docker_compose:
            scanners.append("docker")
        if self.has_kubernetes or self.has_helm:
            scanners.append("kubernetes")
        if (self.has_github_actions or self.has_gitlab_ci or 
            self.has_jenkins or self.has_circleci or 
            self.has_azure_devops or self.has_travis or 
            self.has_drone):
            scanners.append("cicd")

        return scanners

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "detected_stack": self.get_detected_technologies(),
            "docker": self.has_docker,
            "docker_files": self.docker_files,
            "terraform": self.has_terraform,
            "terraform_files": self.terraform_files,
            "kubernetes": self.has_kubernetes,
            "kubernetes_files": self.kubernetes_files,
            "github_actions": self.has_github_actions,
            "github_actions_files": self.github_actions_files,
            "gitlab_ci": self.has_gitlab_ci,
            "gitlab_ci_files": self.gitlab_ci_files,
            "jenkins": self.has_jenkins,
            "jenkins_files": self.jenkins_files,
            "docker_compose": self.has_docker_compose,
            "docker_compose_files": self.docker_compose_files,
            "helm": self.has_helm,
            "helm_files": self.helm_files,
            "ansible": self.has_ansible,
            "ansible_files": self.ansible_files,
            "circleci": self.has_circleci,
            "circleci_files": self.circleci_files,
            "azure_devops": self.has_azure_devops,
            "azure_devops_files": self.azure_devops_files,
            "travis": self.has_travis,
            "travis_files": self.travis_files,
            "drone": self.has_drone,
            "drone_files": self.drone_files,
        }


def detect_technology_stack(files: list[str]) -> TechnologyStack:
    """
    Detect technology stack from file list.

    Args:
        files: List of file paths in repository

    Returns:
        TechnologyStack with detected technologies
    """
    stack = TechnologyStack()

    for file_path in files:
        file_name = file_path.split("/")[-1].lower()
        file_lower = file_path.lower()

        # Docker detection (Dockerfile, Containerfile)
        if file_name in ["dockerfile", "containerfile"] or "dockerfile" in file_name:
            stack.has_docker = True
            stack.docker_files.append(file_path)

        # Docker Compose
        if file_name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
            stack.has_docker_compose = True
            stack.docker_compose_files.append(file_path)

        # Terraform (.tf, .tf.json, .tfvars)
        if file_path.endswith((".tf", ".tf.json", ".tfvars")):
            stack.has_terraform = True
            stack.terraform_files.append(file_path)

        # Kubernetes manifests
        if file_path.endswith((".yaml", ".yml")):
            if _is_kubernetes_manifest(file_path):
                stack.has_kubernetes = True
                stack.kubernetes_files.append(file_path)

        # Helm charts (Chart.yaml, values.yaml in charts/ or helm/ directories)
        if "chart.yaml" in file_name or "values.yaml" in file_name:
            if "charts/" in file_path or "helm/" in file_path or "/chart/" in file_lower:
                stack.has_helm = True
                stack.helm_files.append(file_path)
        
        # Also check for Chart.yaml anywhere (some repos don't follow standard structure)
        if file_name == "chart.yaml":
            stack.has_helm = True
            stack.helm_files.append(file_path)

        # GitHub Actions (.github/workflows/*.yml)
        if ".github/workflows/" in file_path and file_path.endswith((".yml", ".yaml")):
            stack.has_github_actions = True
            stack.github_actions_files.append(file_path)

        # GitLab CI (.gitlab-ci.yml)
        if file_name == ".gitlab-ci.yml" or "/.gitlab-ci.yml" in file_path:
            stack.has_gitlab_ci = True
            stack.gitlab_ci_files.append(file_path)

        # Jenkins (Jenkinsfile, Jenkinsfile-Backend, etc.)
        if file_name == "jenkinsfile" or file_name.startswith("jenkinsfile-"):
            stack.has_jenkins = True
            stack.jenkins_files.append(file_path)

        # CircleCI (.circleci/config.yml)
        if ".circleci/config.yml" in file_path or ".circleci/config.yaml" in file_path:
            stack.has_circleci = True
            stack.circleci_files.append(file_path)

        # Azure DevOps (azure-pipelines.yml)
        if file_name == "azure-pipelines.yml" or file_name == "azure-pipelines.yaml":
            stack.has_azure_devops = True
            stack.azure_devops_files.append(file_path)

        # Travis CI (.travis.yml)
        if file_name == ".travis.yml" or file_name == ".travis.yaml":
            stack.has_travis = True
            stack.travis_files.append(file_path)

        # Drone CI (.drone.yml)
        if file_name == ".drone.yml" or file_name == ".drone.yaml":
            stack.has_drone = True
            stack.drone_files.append(file_path)

        # Ansible (playbooks, roles)
        if file_path.endswith((".yml", ".yaml")) and ("ansible" in file_lower or "playbook" in file_lower or "/roles/" in file_lower):
            stack.has_ansible = True
            stack.ansible_files.append(file_path)

    return stack


def _is_kubernetes_manifest(file_path: str) -> bool:
    """Check if file is likely a Kubernetes manifest based on path and name."""
    file_lower = file_path.lower()

    # Check directory indicators
    k8s_indicators = ["kubernetes", "k8s", "manifests", "deployments", "helm", "charts"]
    if any(indicator in file_lower for indicator in k8s_indicators):
        return True

    # Check file name patterns
    k8s_file_patterns = ["deployment", "service", "pod", "configmap", "secret", "ingress", "namespace", "statefulset", "daemonset", "job", "cronjob"]
    file_name = file_path.split("/")[-1].lower()
    if any(pattern in file_name for pattern in k8s_file_patterns):
        return True

    return False
