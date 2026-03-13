
"""
Repository Scanner - Fetches and detects files in repositories
"""

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RepositoryScanResult:
    """Result of repository scanning."""

    repo_path: str
    repo_url: str
    branch: str
    commit_hash: Optional[str]
    dockerfiles: list[str] = field(default_factory=list)
    terraform_files: list[str] = field(default_factory=list)
    kubernetes_files: list[str] = field(default_factory=list)
    cicd_files: list[str] = field(default_factory=list)
    other_files: list[str] = field(default_factory=list)
    total_files: int = 0
    repo_size_mb: float = 0.0
    scan_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "repo_path": self.repo_path,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "commit_hash": self.commit_hash,
            "dockerfiles": self.dockerfiles,
            "terraform_files": self.terraform_files,
            "kubernetes_files": self.kubernetes_files,
            "cicd_files": self.cicd_files,
            "total_files": self.total_files,
            "repo_size_mb": round(self.repo_size_mb, 2),
            "scan_errors": self.scan_errors,
        }


class RepositoryScanner:
    """Scanner for fetching and analyzing repository structure."""

    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = temp_dir or settings.TEMP_DIR
        os.makedirs(self.temp_dir, exist_ok=True)

    def clone_repository(
        self,
        repo_url: str,
        branch: str = "main",
        commit_hash: Optional[str] = None,
        github_token: Optional[str] = None,
    ) -> tuple[str, RepositoryScanResult]:
        """
        Clone a GitHub repository to temporary storage.

        Args:
            repo_url: GitHub repository URL
            branch: Branch to clone
            commit_hash: Specific commit to checkout (optional)
            github_token: GitHub token for private repos

        Returns:
            Tuple of (repo_path, scan_result)
        """
        import uuid

        # Create unique directory for this scan
        scan_id = str(uuid.uuid4())[:8]
        repo_name = self._extract_repo_name(repo_url)
        repo_path = os.path.join(self.temp_dir, f"{scan_id}_{repo_name}")

        result = RepositoryScanResult(
            repo_path=repo_path,
            repo_url=repo_url,
            branch=branch,
            commit_hash=commit_hash,
        )

        try:
            # Build clone URL with token if provided
            clone_url = repo_url
            if github_token:
                # Insert token into URL
                if repo_url.startswith("https://github.com/"):
                    clone_url = repo_url.replace(
                        "https://github.com/",
                        f"https://x-access-token:{github_token}@github.com/",
                    )

            # Clone repository
            logger.info("Cloning repository", repo_url=repo_url, branch=branch)
            clone_cmd = ["git", "clone", "--depth", "1"]

            if branch:
                clone_cmd.extend(["--branch", branch])

            clone_cmd.extend([clone_url, repo_path])

            subprocess.run(
                clone_cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Checkout specific commit if provided
            if commit_hash:
                logger.info("Checking out commit", commit_hash=commit_hash)
                subprocess.run(
                    ["git", "checkout", commit_hash],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
                result.commit_hash = commit_hash

            # Get actual commit hash
            result.commit_hash = self._get_commit_hash(repo_path)

            # Scan repository for files
            logger.info("Scanning repository for files", repo_path=repo_path)
            self._scan_files(repo_path, result)

            # Calculate repo size
            result.repo_size_mb = self._calculate_dir_size(repo_path)

            # Check size limit
            if result.repo_size_mb > settings.MAX_REPO_SIZE_MB:
                raise ValueError(
                    f"Repository size ({result.repo_size_mb:.1f}MB) exceeds limit ({settings.MAX_REPO_SIZE_MB}MB)"
                )

            logger.info(
                "Repository cloned successfully",
                repo_url=repo_url,
                files=result.total_files,
                size_mb=result.repo_size_mb,
            )

        except subprocess.CalledProcessError as e:
            error_msg = f"Git operation failed: {e.stderr or str(e)}"
            logger.error("Repository clone failed", repo_url=repo_url, error=error_msg)
            result.scan_errors.append(error_msg)
            raise Exception(error_msg)

        except subprocess.TimeoutExpired:
            error_msg = "Repository clone timed out"
            logger.error("Repository clone timed out", repo_url=repo_url)
            result.scan_errors.append(error_msg)
            raise Exception(error_msg)

        except Exception as e:
            logger.error("Repository scan failed", repo_url=repo_url, error=str(e))
            result.scan_errors.append(str(e))
            # Cleanup on error
            self.cleanup(repo_path)
            raise

        return repo_path, result

    def _extract_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL."""
        # Remove .git suffix
        if repo_url.endswith(".git"):
            repo_url = repo_url[:-4]

        # Get last path component
        return repo_url.split("/")[-1]

    def _get_commit_hash(self, repo_path: str) -> Optional[str]:
        """Get current commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    def _scan_files(self, repo_path: str, result: RepositoryScanResult) -> None:
        """Scan repository for analyzable files."""
        repo = Path(repo_path)

        # File patterns to look for
        dockerfile_patterns = ["Dockerfile", "Containerfile", "*.dockerfile"]
        terraform_patterns = ["*.tf", "*.tf.json"]
        kubernetes_patterns = ["*.yaml", "*.yml"]
        cicd_patterns = [
            ".github/workflows/*.yml",
            ".github/workflows/*.yaml",
            ".gitlab-ci.yml",
            ".circleci/config.yml",
            "Jenkinsfile",
            "azure-pipelines.yml",
        ]

        # Directories to scan
        scan_dirs = [repo]
        k8s_dirs = ["kubernetes", "k8s", "manifests", "deployments", "helm"]
        for k8s_dir in k8s_dirs:
            k8s_path = repo / k8s_dir
            if k8s_path.exists():
                scan_dirs.append(k8s_path)

        for file_path in repo.rglob("*"):
            if not file_path.is_file():
                continue

            # Skip hidden directories (except .github)
            if ".git" in str(file_path) and ".github" not in str(file_path):
                continue
            if "__pycache__" in str(file_path):
                continue
            if "node_modules" in str(file_path):
                continue

            rel_path = str(file_path.relative_to(repo))
            file_name = file_path.name

            # Check Dockerfile
            if any(
                file_name == p or file_name.endswith(p)
                for p in dockerfile_patterns
                if "*" not in p
            ) or "dockerfile" in file_name.lower():
                result.dockerfiles.append(rel_path)

            # Check Terraform
            elif file_path.suffix in [".tf", ".tf.json", ".tfvars"]:
                result.terraform_files.append(rel_path)

            # Check Kubernetes
            elif file_path.suffix in [".yaml", ".yml"]:
                # Check if it's in a k8s directory or has k8s content
                if any(indicator in str(file_path).lower() for indicator in k8s_dirs):
                    result.kubernetes_files.append(rel_path)
                elif self._is_kubernetes_manifest(file_path):
                    result.kubernetes_files.append(rel_path)

            # Check CI/CD
            elif any(pattern in str(file_path) for pattern in cicd_patterns):
                result.cicd_files.append(rel_path)
            elif file_name == "Jenkinsfile":
                result.cicd_files.append(rel_path)

            else:
                result.other_files.append(rel_path)

        result.total_files = (
            len(result.dockerfiles) +
            len(result.terraform_files) +
            len(result.kubernetes_files) +
            len(result.cicd_files)
        )

    def _is_kubernetes_manifest(self, file_path: Path) -> bool:
        """Check if file is a Kubernetes manifest."""
        try:
            import yaml
            content = file_path.read_text(encoding="utf-8")
            docs = list(yaml.safe_load_all(content))

            for doc in docs:
                if not doc or not isinstance(doc, dict):
                    continue
                if "apiVersion" in doc and "kind" in doc:
                    return True

        except Exception:
            pass

        return False

    def _calculate_dir_size(self, dir_path: str) -> float:
        """Calculate directory size in MB."""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(dir_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
        return total_size / (1024 * 1024)  # Convert to MB

    def cleanup(self, repo_path: str) -> None:
        """Clean up temporary repository files."""
        try:
            if os.path.exists(repo_path):
                shutil.rmtree(repo_path)
                logger.info("Cleaned up temporary files", path=repo_path)
        except Exception as e:
            logger.warning("Failed to cleanup temporary files", path=repo_path, error=str(e))

    def scan_local_directory(self, dir_path: str) -> RepositoryScanResult:
        """
        Scan a local directory (for testing without git).

        Args:
            dir_path: Path to directory

        Returns:
            RepositoryScanResult
        """
        result = RepositoryScanResult(
            repo_path=dir_path,
            repo_url="local://" + dir_path,
            branch="local",
            commit_hash=None,
        )

        self._scan_files(dir_path, result)
        result.repo_size_mb = self._calculate_dir_size(dir_path)

        return result
