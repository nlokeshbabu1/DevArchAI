"""Canonical technology classifier.

Assigns every file / finding to EXACTLY ONE technology using a strict,
priority-ordered ownership rule. This prevents aggregation bugs where a
single finding is counted under multiple Technology Coverage cards.

Classification priority:
    1. Helm        - Chart.yaml, values.yaml, templates/*, charts/*
    2. Docker      - Dockerfile / Containerfile
    3. GitHub Actions - .github/workflows/*
    4. Terraform   - *.tf, *.tf.json, *.tfvars
    5. Kubernetes  - only native manifest filenames
                    (deployment.yaml, service.yaml, ingress.yaml, daemonset.yaml,
                     statefulset.yaml, configmap.yaml, secret.yaml, cronjob.yaml,
                     namespace.yaml, kustomization.yaml)
    6. Other CI / config file families (unambiguous, no overlap with 1-5)
    7. Directory + resource-kind rescue: a YAML/JSON manifest that lives in a
       Kubernetes/Helm directory and whose filename references a known
       workload kind (deploy*, stateful*, ingress*, ...) belongs to that
       technology even when the exact filename is non-standard (e.g. the
       typo "backend-deployemt.yaml"). Exact filenames always win first.
    8. Scanner-based fallbacks (secrets, dependencies)
    9. code        - anything that does not own a technology

A Helm chart file (Chart.yaml / values.yaml / templates/* / charts/*) is
NEVER counted again as Kubernetes. Ownership is exclusive.
"""

from __future__ import annotations

import re

HELM = "helm"
DOCKER = "docker"
GITHUB_ACTIONS = "github_actions"
TERRAFORM = "terraform"
KUBERNETES = "kubernetes"
GITLAB_CI = "gitlab_ci"
JENKINS = "jenkins"
CIRCLECI = "circleci"
AZURE_DEVOPS = "azure_devops"
DOCKER_COMPOSE = "docker_compose"
ANSIBLE = "ansible"
TRAVIS_CI = "travis_ci"
DRONE_CI = "drone_ci"
PROMETHEUS = "prometheus"
GRAFANA = "grafana"
AWS = "aws"
AZURE = "azure"
GCP = "gcp"
SECRETS = "secrets"
DEPENDENCIES = "dependencies"
CODE = "code"

_DOCKERFILE_NAMES = ("dockerfile", "containerfile")

_TERRAFORM_SUFFIXES = (".tf", ".tf.json", ".tfvars")

# Native Kubernetes manifests. Matching is by filename only so that files
# owned by another technology (e.g. Helm templates) are never captured here.
_NATIVE_K8S_MANIFESTS = (
    "deployment.yaml",
    "service.yaml",
    "ingress.yaml",
    "daemonset.yaml",
    "statefulset.yaml",
    "configmap.yaml",
    "secret.yaml",
    "cronjob.yaml",
    "namespace.yaml",
    "kustomization.yaml",
)

_GITLAB_CI_NAMES = (".gitlab-ci.yml", ".gitlab-ci.yaml")

_CIRCLECI_PATHS = (".circleci",)

_AZURE_DEVOPS_NAMES = ("azure-pipelines.yml", "azure-pipelines.yaml")

_DOCKER_COMPOSE_NAMES = (
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "docker-compose.override.yml",
    "docker-compose.override.yaml",
)

_TRAVIS_NAMES = (".travis.yml", ".travis.yaml")

_DRONE_NAMES = (".drone.yml", ".drone.yaml")

# Directory names that mark a Kubernetes manifests directory.
_KUBERNETES_DIR_SEGMENTS = ("kubernetes", "k8s", "kube")

# Directory names that mark a Helm charts directory ("charts" is already
# owned by the exact-filename Helm rules above).
_HELM_DIR_SEGMENTS = ("helm", "helm-chart", "helm-charts", "chart")

# Filename stems that identify a Kubernetes workload/resource manifest even
# when the full filename is misspelled or suffixed (backend-deployemt.yaml,
# statefullset.yaml, prod-ingress.yaml, ...).
_KIND_STEMS = (
    "deploy",
    "stateful",
    "daemonset",
    "ingress",
    "service",
    "configmap",
    "cronjob",
    "namespace",
    "kustomization",
)

_MANIFEST_SUFFIXES = (".yaml", ".yml", ".json")

_DEPENDENCY_SCANNERS = (
    "npm_audit",
    "pip_audit",
    "govulncheck",
    "dependency_check",
)


def _norm_path(file_path: str | None) -> str:
    """Return a lowercased, forward-slash, repo-relative path for matching."""
    raw = (file_path or "").strip().replace("\\", "/")
    lower = raw.lower()
    # Strip only a leading "./" prefix (never a leading dot of hidden dirs
    # like ".github" or ".gitlab-ci.yml").
    lower = re.sub(r"^(\./)+", "", lower)
    return lower.lstrip("/")


def _basename(path: str) -> str:
    return path.rstrip("/").split("/")[-1]


def _segment(path: str, segment: str) -> bool:
    """True when ``segment`` appears as a full path segment in ``path``."""
    return f"/{segment}/" in f"/{path}"


def _is_helm_file(path: str) -> bool:
    """Helm ownership: Chart.yaml, values.yaml, templates/*, charts/*."""
    name = _basename(path)
    if name == "chart.yaml":
        return True
    if name == "values.yaml":
        return True
    if name in ("helmfile.yaml", "helmfile.yml"):
        return True
    if _segment(path, "templates"):
        return True
    if _segment(path, "charts"):
        return True
    return False


def _is_dockerfile(path: str) -> bool:
    name = _basename(path)
    if name in _DOCKERFILE_NAMES:
        return True
    if name.startswith("dockerfile.") or name.startswith("containerfile."):
        return True
    return name.endswith(".dockerfile")


def _is_native_k8s_manifest(path: str) -> bool:
    """Only the explicit native Kubernetes manifest filenames."""
    name = _basename(path)
    for kind in _NATIVE_K8S_MANIFESTS:
        if name == kind or name.endswith(f"-{kind}"):
            return True
    return False


def classify_technology(file_path: str | None = None, scanner_name: str | None = "") -> str:
    """Classify a file/finding into exactly one canonical technology."""
    path = _norm_path(file_path)
    scanner = (scanner_name or "").lower()

    # 1) Helm - owns Chart.yaml, values.yaml, templates/* and charts/*.
    #    Helm must win over Kubernetes: a chart template is a Helm file, not
    #    a native Kubernetes manifest.
    if _is_helm_file(path):
        return HELM

    # 2) Docker
    if _is_dockerfile(path) or "hadolint" in scanner:
        return DOCKER

    # 3) GitHub Actions
    if path.startswith(".github/workflows/"):
        return GITHUB_ACTIONS

    # 4) Terraform
    if path.endswith(_TERRAFORM_SUFFIXES) or "tfsec" in scanner:
        return TERRAFORM

    # 5) Kubernetes - only native manifest filenames.
    if _is_native_k8s_manifest(path) or "kube_score" in scanner:
        return KUBERNETES

    # 6) Other CI / config file families.
    name = _basename(path)
    if name in _GITLAB_CI_NAMES:
        return GITLAB_CI
    if name == "jenkinsfile" or name.startswith("jenkinsfile-") or _segment(path, "jenkins"):
        return JENKINS
    if any(_segment(path, marker) for marker in _CIRCLECI_PATHS):
        return CIRCLECI
    if name in _AZURE_DEVOPS_NAMES:
        return AZURE_DEVOPS
    if name in _DOCKER_COMPOSE_NAMES:
        return DOCKER_COMPOSE
    if path.endswith((".yml", ".yaml")) and (
        "ansible" in path or "playbook" in path or _segment(path, "roles")
    ):
        return ANSIBLE
    if name in _TRAVIS_NAMES:
        return TRAVIS_CI
    if name in _DRONE_NAMES:
        return DRONE_CI
    if "prometheus" in path:
        return PROMETHEUS
    if "grafana" in path:
        return GRAFANA
    if "aws" in path or "ec2" in path or "s3" in path or "lambda" in path:
        return AWS
    if "azure" in path or "aks" in path:
        return AZURE
    if "gcp" in path or "gke" in path or "google" in path:
        return GCP

    # 6b) Directory + resource-kind rescue. A manifest file whose exact
    #     filename is non-standard (typos, env suffixes) still belongs to the
    #     technology that owns its directory when the filename references a
    #     known workload kind. Exact-filename rules above always win first.
    if path.endswith(_MANIFEST_SUFFIXES) and any(stem in name for stem in _KIND_STEMS):
        if any(_segment(path, seg) for seg in _HELM_DIR_SEGMENTS):
            return HELM
        if any(_segment(path, seg) for seg in _KUBERNETES_DIR_SEGMENTS):
            return KUBERNETES

    # 7) Scanner-based fallbacks (secret/dependency scanners are not
    #    technology files themselves).
    if "gitleaks" in scanner:
        return SECRETS
    if any(marker in scanner for marker in _DEPENDENCY_SCANNERS):
        return DEPENDENCIES

    # 8) No owning technology.
    return CODE
