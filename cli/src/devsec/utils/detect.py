"""Lightweight local technology detection.

The backend runs its own authoritative detection pipeline; this module only
builds a best-effort picture for the user's *local* working tree (and feeds
Phase 2's scan-creation payload). It reads only the same file set the upload
layer would send, bounded per-file to ``MAX_READABLE_FILE_SIZE``.
"""

from __future__ import annotations

import fnmatch
import re
from functools import lru_cache
from pathlib import Path

from devsec.models.detection import DetectedStack
from devsec.utils.filesystem import (
    MAX_READABLE_FILE_SIZE,
    IgnoreMatcher,
    ProjectFile,
    iter_project_files,
    load_devsecignore,
)

# ---------------------------------------------------------------------------
# Pattern tables
# ---------------------------------------------------------------------------

_NAME_PATTERNS: dict[str, tuple[str, ...]] = {
    "docker": ("Dockerfile",),
    "docker_compose": ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"),
    "helm": ("Chart.yaml",),
    "github_actions": (".github/workflows/",),
    "gitlab_ci": (".gitlab-ci.yml",),
    "jenkins": ("Jenkinsfile",),
    "azure_devops": ("azure-pipelines.yml", "azure-pipelines.yaml"),
    "travis": (".travis.yml",),
    "drone": (".drone.yml", ".drone.yaml"),
    "prometheus": ("prometheus.yml", "prometheus.yaml"),
}

_GLOB_PATTERNS: dict[str, tuple[str, ...]] = {
    "docker": ("Dockerfile*", "*.dockerfile"),
    "terraform": ("*.tf", "*.tf.json", "*.tfvars", ".terraform.lock.hcl"),
    "ansible": ("ansible.cfg", "playbook*.yml", "playbook*.yaml", "site.yml", "roles/"),
    "github_actions": (".github/workflows/*.yml", ".github/workflows/*.yaml"),
    "circleci": (".circleci/config.yml",),
    "azure_devops": (
        ".azuredevops/pipelines/*.yml",
        ".azuredevops/pipelines/*.yaml",
        "azure-pipelines/*.yml",
    ),
    "grafana": ("grafana/**", "provisioning/dashboards/**"),
}

# Kubernetes kinds we recognize in YAML manifests.
_K8S_KINDS = (
    "Deployment",
    "Service",
    "StatefulSet",
    "DaemonSet",
    "ReplicaSet",
    "Pod",
    "ConfigMap",
    "Secret",
    "Ingress",
    "CronJob",
    "Job",
    "HorizontalPodAutoscaler",
    "NetworkPolicy",
    "PersistentVolume",
    "PersistentVolumeClaim",
    "Namespace",
    "ServiceAccount",
    "Role",
    "RoleBinding",
    "ClusterRole",
    "ClusterRoleBinding",
    "MutatingWebhookConfiguration",
    "ValidatingWebhookConfiguration",
)

_LANGUAGE_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "python": (".py",),
    "node": (".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"),
    "go": (".go",),
    "java": (".java", ".kt", ".groovy"),
    "ruby": (".rb",),
    "rust": (".rs",),
    "php": (".php",),
}

_RE_API_VERSION = re.compile(r"^\s*apiVersion\s*:", re.MULTILINE)
_RE_KIND = re.compile(r"^\s*kind\s*:\s*([A-Za-z0-9]+)\s*$", re.MULTILINE)
_RE_HELM_CHART = re.compile(r"^\s*(apiVersion|name|version)\s*:", re.MULTILINE)
_RE_GRAFANA = re.compile(r'"(title|uid|panels|schemaVersion|dashboard)"', re.MULTILINE)


def _sample_files(files: list[ProjectFile]) -> list[ProjectFile]:
    """Files eligible for content sniffing, bounded in size and count."""
    return [f for f in files if f.size <= MAX_READABLE_FILE_SIZE][:500]


def _read_head(file: ProjectFile, limit: int = 16 * 1024) -> str:
    try:
        with open(file.abs_path, encoding="utf-8", errors="ignore") as fh:
            return fh.read(limit)
    except OSError:
        return ""


def _matches_any(file: ProjectFile, patterns: tuple[str, ...]) -> bool:
    rel = file.rel_path
    for pat in patterns:
        if pat.endswith("/"):
            if rel.startswith(pat):
                return True
        elif rel == pat or fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, f"**/{pat}"):
            return True
    return False


def _collect(files: list[ProjectFile], key: str) -> list[ProjectFile]:
    names = _NAME_PATTERNS.get(key, ())
    globs = _GLOB_PATTERNS.get(key, ())
    return [f for f in files if _matches_any(f, names + globs)]


def _detect_languages(files: list[ProjectFile]) -> list[str]:
    counts: dict[str, int] = {}
    for f in files:
        ext = f.rel_path.rsplit(".", 1)[-1] if "." in f.rel_path else ""
        suffix = f".{ext}"
        for lang, exts in _LANGUAGE_EXTENSIONS.items():
            if suffix in exts:
                counts[lang] = counts.get(lang, 0) + 1
                break
    total = sum(counts.values())
    if total == 0:
        return []
    ordered = sorted(counts, key=lambda lang: (-counts[lang], lang))
    # Keep languages that make up at least 5% of source files.
    return [lang for lang in ordered if counts[lang] / total >= 0.05]


@lru_cache(maxsize=32)
def detect_stack(root: str) -> DetectedStack:
    """Detect the technology stack present under ``root`` (cached per path)."""
    root_path = Path(root).resolve()
    matcher = IgnoreMatcher(load_devsecignore(root_path))
    files = iter_project_files(root_path, matcher=matcher)
    by_name = {f.rel_path: f for f in files}
    sample = _sample_files(files)

    detected = DetectedStack(
        file_count=len(files),
        files_analyzed=len(files),
        total_size_bytes=sum(f.size for f in files),
        languages=_detect_languages(files),
    )

    for tech in (
        "docker",
        "docker_compose",
        "terraform",
        "helm",
        "github_actions",
        "gitlab_ci",
        "jenkins",
        "circleci",
        "azure_devops",
        "travis",
        "drone",
        "prometheus",
        "grafana",
    ):
        found = _collect(files, tech)
        if found:
            setattr(detected, f"has_{tech}", True)
            setattr(detected, f"{tech}_files", [f.rel_path for f in found])

    # Dockerfile-like names fall under has_docker even without exact "Dockerfile".
    docker = by_name.get("Dockerfile")
    if docker is not None:
        detected.docker_files = [docker.rel_path]

    # Ansible via directory heuristics.
    if any(rel.startswith("roles/") for rel in by_name) and not detected.has_ansible:
        detected.has_ansible = True
        detected.ansible_files = [rel for rel in by_name if rel.startswith("roles/")][:20]

    # Kubernetes: sniff manifest content.
    k8s_files: list[str] = []
    yaml_candidates = [
        f
        for f in sample
        if f.rel_path.endswith((".yml", ".yaml"))
        and f.rel_path
        not in (
            set(detected.github_actions_files)
            | set(detected.circleci_files)
            | set(detected.gitlab_ci_files)
            | set(detected.drone_files)
        )
    ]
    for f in yaml_candidates:
        text = _read_head(f)
        if not _RE_API_VERSION.search(text):
            continue
        kind = _RE_KIND.search(text)
        if kind and kind.group(1) in _K8S_KINDS:
            k8s_files.append(f.rel_path)
    if k8s_files:
        detected.has_kubernetes = True
        detected.kubernetes_files = k8s_files[:50]

    # Helm detection requires a parseable Chart.yaml.
    if detected.has_helm:
        helm_files = _collect(files, "helm")
        valid = [
            f.rel_path
            for f in helm_files
            if f.rel_path.endswith("Chart.yaml") and _RE_HELM_CHART.search(_read_head(f))
        ]
        detected.helm_files = valid
        if not valid:
            detected.has_helm = False

    # Grafana: prefer dashboards with recognizable structure.
    if detected.has_grafana:
        grafana_files = _collect(files, "grafana")
        jsonish = [
            f.rel_path
            for f in grafana_files
            if f.rel_path.endswith(".json") and _RE_GRAFANA.search(_read_head(f))
        ]
        if jsonish:
            detected.grafana_files = jsonish[:50]

    return detected
