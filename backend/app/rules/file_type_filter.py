"""
File-Type Based Rule Filtering

Maps file types to their relevant rule modules and ensures rules only run on appropriate files.
"""

from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


# File type definitions with their extensions and patterns
FILE_TYPE_DEFINITIONS = {
    "terraform": {
        "extensions": {".tf", ".tf.json"},
        "patterns": ["*.tf", "*.tf.json"],
    },
    "terraform_vars": {
        "extensions": {".tfvars"},
        "patterns": ["*.tfvars"],
    },
    "dockerfile": {
        "extensions": set(),
        "filenames": {"Dockerfile", "Containerfile", "dockerfile"},
        "patterns": ["*Dockerfile*", "*Containerfile*"],
    },
    "kubernetes": {
        "extensions": {".yaml", ".yml"},
        "directory_patterns": ["kubernetes", "k8s", "manifests", "deployments", "helm", "charts"],
        "content_indicators": ["apiVersion", "kind"],
    },
    "cicd": {
        "extensions": {".yaml", ".yml"},
        "path_patterns": [".github/workflows/", ".gitlab-ci.yml", ".circleci/", "Jenkinsfile"],
        "filenames": {".gitlab-ci.yml", "Jenkinsfile", "azure-pipelines.yml"},
    },
    "docker_compose": {
        "extensions": {".yaml", ".yml"},
        "filenames": {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"},
    },
    "helm": {
        "extensions": {".yaml", ".yml"},
        "directory_patterns": ["charts/", "helm/"],
        "filenames": {"Chart.yaml", "values.yaml"},
    },
}

# Rule modules mapped to file types
RULE_MODULE_MAP = {
    "terraform": ["app.rules.terraform", "app.rule_engine.rules.terraform_rules"],
    "dockerfile": ["app.rules.dockerfile", "app.rule_engine.rules.docker_rules"],
    "kubernetes": ["app.rules.kubernetes", "app.rule_engine.rules.kubernetes_rules"],
    "cicd": ["app.rules.cicd", "app.rule_engine.rules.cicd_rules"],
    "docker_compose": ["app.rules.dockerfile"],
    "helm": ["app.rules.kubernetes"],
}

# Files to ignore (documentation, etc.)
IGNORE_PATTERNS = {
    "extensions": {".md", ".txt", ".rst", ".adoc", ".log"},
    "filenames": {"README", "README.md", "CHANGELOG.md", "LICENSE", "CONTRIBUTING.md", ".gitignore", "Makefile"},
    "directories": {".git", "node_modules", "__pycache__", ".pytest_cache", ".venv", "venv", "dist", "build", ".terraform"},
}


def detect_file_type(file_path: str) -> str | None:
    """
    Detect the file type based on path, extension, and name.

    Args:
        file_path: Path to the file

    Returns:
        File type string or None if not recognized/should be ignored
    """
    path = Path(file_path)
    file_name = path.name.lower()
    file_suffix = path.suffix.lower()
    path_str = str(file_path).lower()

    # Check if file should be ignored first
    if should_ignore(file_path):
        return None

    # Check Dockerfile (no extension typically)
    # Use lowercase comparison
    dockerfile_filenames = {f.lower() for f in FILE_TYPE_DEFINITIONS["dockerfile"]["filenames"]}
    if file_name in dockerfile_filenames or "dockerfile" in file_name:
        return "dockerfile"

    # Check docker-compose
    compose_filenames = {f.lower() for f in FILE_TYPE_DEFINITIONS["docker_compose"]["filenames"]}
    if file_name in compose_filenames:
        return "docker_compose"

    # Check Terraform files (.tf, .tf.json)
    if file_suffix in FILE_TYPE_DEFINITIONS["terraform"]["extensions"]:
        return "terraform"

    # Also check for .tf.json (suffix would be .json, so check full name)
    if file_name.endswith(".tf.json"):
        return "terraform"

    # Check Terraform vars (.tfvars)
    if file_suffix in FILE_TYPE_DEFINITIONS["terraform_vars"]["extensions"]:
        return "terraform_vars"

    # Check CI/CD (before Kubernetes because both use YAML)
    cicd_filenames = {f.lower() for f in FILE_TYPE_DEFINITIONS["cicd"]["filenames"]}
    for pattern in FILE_TYPE_DEFINITIONS["cicd"]["path_patterns"]:
        if pattern.lower() in path_str:
            return "cicd"
    if file_name in cicd_filenames:
        return "cicd"

    # Check Helm (before Kubernetes because both use YAML in charts/ directories)
    helm_filenames = {f.lower() for f in FILE_TYPE_DEFINITIONS["helm"]["filenames"]}
    for dir_pattern in FILE_TYPE_DEFINITIONS["helm"]["directory_patterns"]:
        if dir_pattern.lower() in path_str and file_name in helm_filenames:
            return "helm"

    # Check Kubernetes (YAML in k8s directories)
    if file_suffix in FILE_TYPE_DEFINITIONS["kubernetes"]["extensions"]:
        for dir_pattern in FILE_TYPE_DEFINITIONS["kubernetes"]["directory_patterns"]:
            if dir_pattern.lower() in path_str:
                return "kubernetes"

    return None


def should_ignore(file_path: str) -> bool:
    """
    Check if a file should be ignored (documentation, etc.).

    Args:
        file_path: Path to the file

    Returns:
        True if file should be ignored
    """
    path = Path(file_path)
    file_name = path.name
    file_suffix = path.suffix.lower()
    path_str = str(file_path).lower()

    # Check extension
    if file_suffix in IGNORE_PATTERNS["extensions"]:
        return True

    # Check filename
    if file_name in IGNORE_PATTERNS["filenames"]:
        return True

    # Check directory - but allow .github (for CI/CD workflows)
    for dir_pattern in IGNORE_PATTERNS["directories"]:
        # Skip .git check if it's .github (for GitHub Actions) or .gitlab-ci.yml
        if dir_pattern == ".git":
            if ".github/" in path_str:
                continue
            # Don't ignore .gitlab-ci.yml or other CI/CD files that start with .
            if file_name.startswith(".git"):
                continue
        if dir_pattern in path_str:
            return True

    return False


def get_applicable_rule_modules(file_path: str) -> list[str]:
    """
    Get list of rule modules that should be applied to this file.

    Args:
        file_path: Path to the file

    Returns:
        List of rule module paths
    """
    file_type = detect_file_type(file_path)

    if not file_type:
        return []

    # Get rule modules for this file type
    rule_modules = RULE_MODULE_MAP.get(file_type, [])

    # For terraform_vars, use terraform rules but only for secrets detection
    if file_type == "terraform_vars":
        rule_modules = ["app.rules.terraform"]  # Limited rules for tfvars

    return rule_modules


def filter_files_by_type(file_paths: list[str], file_type: str) -> list[str]:
    """
    Filter a list of files by type.

    Args:
        file_paths: List of file paths
        file_type: File type to filter by

    Returns:
        Filtered list of file paths
    """
    return [path for path in file_paths if detect_file_type(path) == file_type]


def categorize_files(file_paths: list[str]) -> dict[str, list[str]]:
    """
    Categorize files by their detected type.

    Args:
        file_paths: List of file paths

    Returns:
        Dictionary mapping file types to lists of file paths
    """
    categorized: dict[str, list[str]] = {
        "terraform": [],
        "terraform_vars": [],
        "dockerfile": [],
        "kubernetes": [],
        "cicd": [],
        "docker_compose": [],
        "helm": [],
        "other": [],
        "ignored": [],
    }

    for file_path in file_paths:
        if should_ignore(file_path):
            categorized["ignored"].append(file_path)
            continue

        file_type = detect_file_type(file_path)
        if file_type:
            if file_type in categorized:
                categorized[file_type].append(file_path)
            else:
                categorized["other"].append(file_path)
        else:
            categorized["other"].append(file_path)

    # Remove empty categories for cleaner output
    return {k: v for k, v in categorized.items() if v}


def get_rule_file_type_mapping() -> dict[str, set[str]]:
    """
    Get mapping of rule categories to file types they apply to.

    Returns:
        Dictionary mapping rule categories to file types
    """
    return {
        "terraform": {"terraform"},
        "terraform_vars": {"terraform_vars"},
        "dockerfile": {"dockerfile"},
        "kubernetes": {"kubernetes", "helm"},
        "cicd": {"cicd"},
        "security": {"terraform", "dockerfile", "kubernetes", "cicd"},
        "reliability": {"terraform", "kubernetes", "cicd"},
        "cost": {"terraform", "cicd"},
        "observability": {"terraform", "kubernetes", "cicd"},
    }


class FileTypeRuleFilter:
    """
    Filter that ensures rules only run on appropriate file types.

    This is the main class used by the rule engine to filter rules.
    """

    def __init__(self):
        self._file_type_cache: dict[str, str | None] = {}

    def get_file_type(self, file_path: str) -> str | None:
        """Get file type with caching."""
        if file_path not in self._file_type_cache:
            self._file_type_cache[file_path] = detect_file_type(file_path)
        return self._file_type_cache[file_path]

    def should_apply_rule(
        self,
        rule_id: str,
        rule_file_types: list[str],
        file_path: str,
    ) -> bool:
        """
        Check if a rule should be applied to a file.

        Args:
            rule_id: Rule identifier
            rule_file_types: List of file types the rule applies to
            file_path: Path to the file

        Returns:
            True if rule should be applied
        """
        # If rule has no file type restrictions, apply to all
        if not rule_file_types:
            return True

        # Get file type
        file_type = self.get_file_type(file_path)

        # If file type not recognized, don't apply specialized rules
        if not file_type:
            return False

        # Check if file type matches
        return file_type in rule_file_types

    def get_applicable_rules(self, rules: list, file_path: str) -> list:
        """
        Get list of rules that should be applied to a file.

        Args:
            rules: List of rule objects
            file_path: Path to the file

        Returns:
            Filtered list of rules
        """
        file_type = self.get_file_type(file_path)

        # If file type not recognized, return empty list
        if not file_type:
            return []

        applicable = []
        for rule in rules:
            # Check if rule applies to this file type
            rule_file_types = getattr(rule, "file_types", [])

            # If rule has no file type restriction, check by module
            if not rule_file_types:
                rule_module = rule.__module__
                if file_type in rule_module:
                    applicable.append(rule)
            elif file_type in rule_file_types:
                applicable.append(rule)

        return applicable


# Global filter instance
rule_filter = FileTypeRuleFilter()
