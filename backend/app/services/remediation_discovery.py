"""
Dynamic repository discovery for remediation (repository-agnostic).

Evidence is collected from the cloned tree at a specific commit; results are keyed
by repository root path + commit SHA so stale context is not reused across commits.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from app.services.technology_detector import TechnologyStack, detect_technology_stack

logger = structlog.get_logger(__name__)

MAX_WALK_FILES = 25_000
MAX_FILE_BYTES_FOR_SNIPPET = 512_000


@dataclass
class RepositoryDiscovery:
    repo_root: str
    commit_sha: str
    branch: str | None
    file_paths: list[str] = field(default_factory=list)
    stack: TechnologyStack | None = None
    languages: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    ci_platforms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        stack_dict = self.stack.to_dict() if self.stack else {}
        return {
            "repo_root_fingerprint": _root_fingerprint(self.repo_root),
            "commit_sha": self.commit_sha,
            "branch": self.branch,
            "file_count": len(self.file_paths),
            "languages": self.languages,
            "package_managers": self.package_managers,
            "ci_platforms": self.ci_platforms,
            "technology_stack": stack_dict,
        }


def _root_fingerprint(repo_root: str) -> str:
    return str(Path(repo_root).resolve())


def _is_safe_repo_path(repo_root: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(repo_root.resolve())
        return True
    except ValueError:
        return False


def _walk_repo_files(repo_root: Path) -> list[str]:
    paths: list[str] = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {".git", "node_modules", "vendor"}]
        rel_root = Path(root).relative_to(repo_root)
        for name in files:
            if len(paths) >= MAX_WALK_FILES:
                return paths
            rel = (rel_root / name).as_posix()
            if rel.startswith("../"):
                continue
            paths.append(rel)
    return paths


def _infer_languages(file_paths: list[str]) -> list[str]:
    ext_map = {
        ".go": "go",
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".java": "java",
        ".rb": "ruby",
        ".rs": "rust",
        ".php": "php",
        ".cs": "csharp",
        ".tf": "terraform",
        ".hcl": "hcl",
    }
    found: set[str] = set()
    for p in file_paths:
        suffix = Path(p).suffix.lower()
        if suffix in ext_map:
            found.add(ext_map[suffix])
        if Path(p).name.lower() in {"dockerfile", "containerfile"}:
            found.add("dockerfile")
    return sorted(found)


def _infer_package_managers(file_paths: list[str]) -> list[str]:
    markers = {
        "go.mod": "go_modules",
        "package.json": "npm",
        "pnpm-lock.yaml": "pnpm",
        "yarn.lock": "yarn",
        "requirements.txt": "pip",
        "pyproject.toml": "python_packaging",
        "Gemfile": "bundler",
        "Cargo.toml": "cargo",
        "pom.xml": "maven",
    }
    names = {Path(p).name for p in file_paths}
    return sorted({v for k, v in markers.items() if k in names})


def discover_repository(
    repo_root: str,
    *,
    commit_sha: str,
    branch: str | None = None,
    scan_detected_stack: dict[str, Any] | None = None,
) -> RepositoryDiscovery:
    """
    Discover repository characteristics from the cloned tree at ``commit_sha``.

    ``scan_detected_stack`` is optional metadata from the scan record; file evidence
    from the clone always takes precedence for remediation decisions.
    """
    root = Path(repo_root)
    if not root.is_dir():
        raise ValueError(f"Repository root does not exist: {repo_root}")

    file_paths = _walk_repo_files(root)
    stack = detect_technology_stack(file_paths)

    ci_platforms: list[str] = []
    if stack.has_github_actions:
        ci_platforms.append("github_actions")
    if stack.has_gitlab_ci:
        ci_platforms.append("gitlab_ci")
    if stack.has_jenkins:
        ci_platforms.append("jenkins")
    if stack.has_circleci:
        ci_platforms.append("circleci")
    if stack.has_azure_devops:
        ci_platforms.append("azure_devops")

    discovery = RepositoryDiscovery(
        repo_root=str(root.resolve()),
        commit_sha=commit_sha,
        branch=branch,
        file_paths=file_paths,
        stack=stack,
        languages=_infer_languages(file_paths),
        package_managers=_infer_package_managers(file_paths),
        ci_platforms=ci_platforms,
    )

    if scan_detected_stack and not discovery.languages and scan_detected_stack.get("detected_stack"):
        logger.info(
            "Using scan detected_stack as supplemental context",
            commit_sha=commit_sha,
            stack=scan_detected_stack.get("detected_stack"),
        )

    return discovery


def read_repo_file(repo_root: str, rel_path: str, *, max_bytes: int = MAX_FILE_BYTES_FOR_SNIPPET) -> str | None:
    root = Path(repo_root).resolve()
    target = (root / rel_path).resolve()
    if not _is_safe_repo_path(root, target) or not target.is_file():
        return None
    data = target.read_bytes()
    if len(data) > max_bytes:
        return data[:max_bytes].decode("utf-8", errors="replace")
    return data.decode("utf-8", errors="replace")


def related_files_for_path(discovery: RepositoryDiscovery, rel_path: str, *, limit: int = 8) -> list[str]:
    """Return same-directory and technology-related paths (advisory context)."""
    rel = rel_path.replace("\\", "/")
    directory = str(Path(rel).parent).replace("\\", "/")
    if directory == ".":
        directory = ""

    same_dir: list[str] = []
    for p in discovery.file_paths:
        if directory and p.startswith(directory + "/"):
            if p != rel:
                same_dir.append(p)
        elif not directory and "/" not in p and p != rel:
            same_dir.append(p)
        if len(same_dir) >= limit:
            break

    related: list[str] = list(same_dir[:limit])
    stack = discovery.stack
    if stack:
        tech_lists = (
            stack.docker_files,
            stack.terraform_files,
            stack.kubernetes_files,
            stack.helm_files,
            stack.github_actions_files,
        )
        for lst in tech_lists:
            for p in lst:
                if p != rel and p not in related:
                    related.append(p)
                if len(related) >= limit:
                    return related[:limit]
    return related[:limit]


def discovery_cache_key(repo_url: str, commit_sha: str) -> str:
    return json.dumps({"repo_url": repo_url, "commit_sha": commit_sha}, sort_keys=True)
