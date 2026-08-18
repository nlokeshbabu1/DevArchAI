"""Local repository detection models.

These models describe what the CLI detects about a local working tree. The
backend already runs its own authoritative detection pipeline, so the CLI
keeps this lightweight and only *reports* its findings (Phase 2 will attach
``to_backend_dict()`` output to scan creation).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# Technology names reported to the user (stable identifiers).
DETECTED_TECHNOLOGIES = [
    "docker",
    "terraform",
    "kubernetes",
    "helm",
    "docker_compose",
    "ansible",
    "github_actions",
    "gitlab_ci",
    "jenkins",
    "circleci",
    "azure_devops",
    "travis",
    "drone",
    "prometheus",
    "grafana",
]

DETECTED_LANGUAGES = ["python", "node", "go", "java", "ruby", "rust", "php"]


class DetectedStack(BaseModel):
    """Technology stack detected in a local repository."""

    model_config = ConfigDict(extra="ignore")

    has_docker: bool = False
    docker_files: list[str] = Field(default_factory=list)
    has_docker_compose: bool = False
    docker_compose_files: list[str] = Field(default_factory=list)
    has_terraform: bool = False
    terraform_files: list[str] = Field(default_factory=list)
    has_kubernetes: bool = False
    kubernetes_files: list[str] = Field(default_factory=list)
    has_helm: bool = False
    helm_files: list[str] = Field(default_factory=list)
    has_ansible: bool = False
    ansible_files: list[str] = Field(default_factory=list)
    has_github_actions: bool = False
    github_actions_files: list[str] = Field(default_factory=list)
    has_gitlab_ci: bool = False
    gitlab_ci_files: list[str] = Field(default_factory=list)
    has_jenkins: bool = False
    jenkins_files: list[str] = Field(default_factory=list)
    has_circleci: bool = False
    circleci_files: list[str] = Field(default_factory=list)
    has_azure_devops: bool = False
    azure_devops_files: list[str] = Field(default_factory=list)
    has_travis: bool = False
    travis_files: list[str] = Field(default_factory=list)
    has_drone: bool = False
    drone_files: list[str] = Field(default_factory=list)
    has_prometheus: bool = False
    prometheus_files: list[str] = Field(default_factory=list)
    has_grafana: bool = False
    grafana_files: list[str] = Field(default_factory=list)

    languages: list[str] = Field(default_factory=list)
    file_count: int = 0
    files_analyzed: int = 0
    total_size_bytes: int = 0

    @property
    def technologies(self) -> list[str]:
        """Human-friendly list of detected technologies."""
        found: list[str] = []
        for name in DETECTED_TECHNOLOGIES:
            flag = getattr(self, f"has_{name}")
            if flag:
                found.append(name)
        return found

    def to_backend_dict(self) -> dict:
        """Return a dict compatible with the backend detected_stack schema."""
        return self.model_dump(
            exclude={"languages", "file_count", "files_analyzed", "total_size_bytes"}
        )

    def summary(self) -> str:
        """Short one-line summary for CLI output."""
        if not self.technologies:
            return "No supported technologies detected"
        return ", ".join(self.technologies)
