"""
Technology-based scanner selection and applicability detection.

Detects which external scanners should run based on the files
present in the repository and the DetectedTechnologyStack.
Also returns applicability info for ALL scanners so that
non-applicable scanners are explicitly marked as SKIPPED_NOT_APPLICABLE.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.scanners.models import ApplicabilityInfo

SCA_MANIFEST_MAP: dict[str, list[str]] = {
    "package.json": ["npm_audit"],
    "yarn.lock": ["npm_audit"],
    "pnpm-lock.yaml": ["npm_audit"],
    "requirements.txt": ["pip_audit"],
    "requirement.txt": ["pip_audit"],  # common misspelling
    "Pipfile": ["pip_audit"],
    "Pipfile.lock": ["pip_audit"],
    "poetry.lock": ["pip_audit"],
    "pyproject.toml": ["pip_audit"],
    "go.mod": ["govulncheck"],
    "go.sum": ["govulncheck"],
    "pom.xml": ["dependency_check"],
    "build.gradle": ["dependency_check"],
    "build.gradle.kts": ["dependency_check"],
    "gradle.lockfile": ["dependency_check"],
    "Cargo.lock": ["dependency_check"],
    "composer.lock": ["dependency_check"],
    "Gemfile.lock": ["dependency_check"],
}


def detect_sca_scanners(repo_path: Path) -> list[str]:
    """Detect which SCA scanners to run based on manifest files in the repo."""
    scanners: list[str] = []
    seen: set[str] = set()

    for manifest, scs in SCA_MANIFEST_MAP.items():
        if any(repo_path.rglob(manifest)):
            for s in scs:
                if s not in seen:
                    scanners.append(s)
                    seen.add(s)

    return scanners


def _check_has_terraform_files(repo_path: Path) -> bool:
    """Check if the repo contains .tf files."""
    try:
        return len(list(repo_path.rglob("*.tf"))) > 0
    except (PermissionError, OSError):
        return False


def _check_has_kubernetes_files(repo_path: Path) -> bool:
    """Check if the repo has Kubernetes manifests or Helm charts."""
    try:
        k8s_patterns = ["deployment.yaml", "service.yaml", "kustomization.yaml", "ingress.yaml", "configmap.yaml"]
        for p in k8s_patterns:
            if list(repo_path.rglob(p)):
                return True
        if (repo_path / "helm").is_dir() or (repo_path / "charts").is_dir():
            return True
        # Check for common k8s apiVersion references
        yaml_files = list(repo_path.rglob("*.yaml"))[:20]
        for yf in yaml_files:
            try:
                text = yf.read_text(encoding="utf-8", errors="ignore")[:2000]
                if "apiVersion:" in text and any(k in text for k in ["Deployment", "Service", "Pod", "Namespace", "Ingress", "ConfigMap"]):
                    return True
            except Exception:
                continue
    except (PermissionError, OSError):
        pass
    return False


def _check_has_docker_files(repo_path: Path) -> bool:
    """Check if the repo contains Dockerfile or docker-compose files."""
    try:
        docker_patterns = ["Dockerfile*", "docker-compose*", "*.dockerfile"]
        for p in docker_patterns:
            if list(repo_path.rglob(p)):
                return True
        # Also check typical Dockerfile paths
        if (repo_path / "Dockerfile").exists():
            return True
    except (PermissionError, OSError):
        pass
    return False


def _check_has_github_actions(repo_path: Path) -> bool:
    """Check if the repo has GitHub Actions workflows."""
    workflows_dir = repo_path / ".github" / "workflows"
    try:
        return workflows_dir.is_dir() and len(list(workflows_dir.glob("*.yml"))) + len(list(workflows_dir.glob("*.yaml"))) > 0
    except (PermissionError, OSError):
        return False


def get_scanner_applicability(
    repo_path: Path,
    detected_stack: dict[str, Any] | None,
) -> dict[str, ApplicabilityInfo]:
    """Determine applicability for ALL known scanners, with explicit reasons.

    Returns:
        Dict mapping scanner_id -> ApplicabilityInfo(applicable, reason).
    """
    if detected_stack is None:
        detected_stack = {}

    has_docker = detected_stack.get("has_docker", False) or _check_has_docker_files(repo_path)
    has_terraform = detected_stack.get("has_terraform", False) or _check_has_terraform_files(repo_path)
    has_kubernetes = detected_stack.get("has_kubernetes", False) or _check_has_kubernetes_files(repo_path)
    has_github_actions = _check_has_github_actions(repo_path)

    sca_scanners = detect_sca_scanners(repo_path)

    applicability: dict[str, ApplicabilityInfo] = {}

    # -- Docker / Container scanners --
    if has_docker:
        applicability["hadolint"] = ApplicabilityInfo(applicable=True)
        applicability["checkov"] = ApplicabilityInfo(applicable=True)
        applicability["trivy_filesystem"] = ApplicabilityInfo(applicable=True)
    else:
        applicability["hadolint"] = ApplicabilityInfo(applicable=False, reason="No Dockerfile detected.")
        # checkov/trivy_filesystem may still be applicable via other tech
        if not has_terraform and not has_kubernetes:
            applicability["checkov"] = ApplicabilityInfo(applicable=False, reason="No Docker, Terraform, or Kubernetes files detected.")
            applicability["trivy_config"] = ApplicabilityInfo(applicable=False, reason="No Kubernetes files detected.")

    # -- Terraform scanners --
    if has_terraform:
        applicability["checkov"] = ApplicabilityInfo(applicable=True)
        applicability["tfsec"] = ApplicabilityInfo(applicable=True)
    else:
        if "tfsec" not in applicability:
            applicability["tfsec"] = ApplicabilityInfo(applicable=False, reason="No Terraform (.tf) files detected.")

    # -- Kubernetes scanners --
    if has_kubernetes:
        applicability["kube_score"] = ApplicabilityInfo(applicable=True)
        applicability["checkov"] = ApplicabilityInfo(applicable=True)
        applicability["trivy_config"] = ApplicabilityInfo(applicable=True)
    else:
        if "kube_score" not in applicability:
            applicability["kube_score"] = ApplicabilityInfo(applicable=False, reason="No Kubernetes manifests detected.")
        if "trivy_config" not in applicability:
            applicability["trivy_config"] = ApplicabilityInfo(applicable=False, reason="No Kubernetes manifests detected.")

    # -- SCA scanners (manifest-based) --
    sca_manifest_map = {
        "npm_audit": ("package.json", "Node.js"),
        "pip_audit": ("requirements.txt / Pipfile / pyproject.toml", "Python"),
        "govulncheck": ("go.mod / go.sum", "Go"),
        "dependency_check": ("pom.xml / build.gradle", "Java"),
    }
    for scanner_id, (manifest_name, tech_name) in sca_manifest_map.items():
        if scanner_id in sca_scanners:
            applicability[scanner_id] = ApplicabilityInfo(applicable=True)
        else:
            applicability[scanner_id] = ApplicabilityInfo(
                applicable=False,
                reason=f"No {manifest_name} detected (no {tech_name} project found).",
            )

    # -- CI/CD scanners --
    if has_github_actions:
        applicability["gitleaks"] = ApplicabilityInfo(applicable=True)
    else:
        if "gitleaks" not in applicability:
            applicability["gitleaks"] = ApplicabilityInfo(applicable=True)  # always runs

    # -- Always-run scanners (if not already set) --
    always_run = {
        "gitleaks": "Secret scanning runs on all repositories.",
        "trivy_filesystem": "Filesystem vulnerability scanning runs on all repositories.",
    }
    for sid, _reason in always_run.items():
        if sid not in applicability:
            applicability[sid] = ApplicabilityInfo(applicable=True)

    # Fill in checkov if not yet set (it was checked above)
    if "checkov" not in applicability:
        applicability["checkov"] = ApplicabilityInfo(applicable=True, reason="Runs on Docker, Terraform, and Kubernetes files.")

    # Fill in trivy_filesystem if not yet set
    if "trivy_filesystem" not in applicability:
        applicability["trivy_filesystem"] = ApplicabilityInfo(applicable=True, reason="Filesystem vulnerability scanning runs on all repositories.")

    return applicability


def get_scanners_for_stack(
    repo_path: Path,
    detected_stack: dict[str, Any] | None,
) -> list[str]:
    """Determine which external scanners to run based on the technology stack.

    Args:
        repo_path: Path to the cloned repository.
        detected_stack: DetectedTechnologyStack.to_dict() or None.

    Returns:
        Sorted list of scanner IDs to run (only applicable scanners).
    """
    applicability = get_scanner_applicability(repo_path, detected_stack)
    return sorted([sid for sid, info in applicability.items() if info.applicable])


def get_skipped_scanners(
    repo_path: Path,
    detected_stack: dict[str, Any] | None,
) -> dict[str, str]:
    """Return scanners that are NOT applicable, with skip reasons.

    Returns:
        Dict mapping scanner_id -> skip_reason.
    """
    applicability = get_scanner_applicability(repo_path, detected_stack)
    return {
        sid: info.reason
        for sid, info in applicability.items()
        if not info.applicable and info.reason
    }
