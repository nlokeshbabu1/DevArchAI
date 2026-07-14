"""
Terraform Module Detection

Detects Terraform root modules and groups files by module directory.
"""

from dataclasses import dataclass, field
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class TerraformModule:
    """Represents a Terraform root module."""

    module_path: str  # Relative path to module directory
    tf_files: list[str] = field(default_factory=list)
    has_backend: bool = False
    backend_type: str | None = None
    is_root_module: bool = True

    def to_dict(self) -> dict:
        return {
            "module_path": self.module_path,
            "tf_files": self.tf_files,
            "has_backend": self.has_backend,
            "backend_type": self.backend_type,
            "is_root_module": self.is_root_module,
        }


def is_inside_modules_dir(file_path: str) -> bool:
    """Check if a file path is inside a modules/ directory."""
    path_parts = Path(file_path).parts
    return "modules" in path_parts


def detect_terraform_modules(repo_path: Path, tf_files: list[str]) -> dict[str, TerraformModule]:
    """
    Detect Terraform root modules from a list of .tf files.

    A root module is a directory containing .tf files that is NOT inside a modules/ directory.

    Args:
        repo_path: Repository root path
        tf_files: List of .tf file paths (relative to repo_path)

    Returns:
        Dictionary mapping module directory to TerraformModule
    """
    modules: dict[str, TerraformModule] = {}

    for tf_file in tf_files:
        # Skip files inside modules/ directories
        if is_inside_modules_dir(tf_file):
            continue

        # Get the directory of this .tf file
        file_path = Path(tf_file)
        module_dir = str(file_path.parent) if file_path.parent != Path('.') else '.'

        # Create or update module
        if module_dir not in modules:
            modules[module_dir] = TerraformModule(
                module_path=module_dir,
                tf_files=[],
                has_backend=False,
                backend_type=None,
                is_root_module=True,
            )

        modules[module_dir].tf_files.append(tf_file)

    return modules


def scan_module_backends(repo_path: Path, modules: dict[str, TerraformModule],
                         parsed_files: list) -> dict[str, TerraformModule]:
    """
    Scan parsed files to detect backend configuration in each module.

    Args:
        repo_path: Repository root path
        modules: Dictionary of detected modules
        parsed_files: List of parsed file objects

    Returns:
        Updated modules dictionary with backend information
    """
    for parsed_file in parsed_files:
        if parsed_file.file_type != "terraform":
            continue

        # Get relative path
        file_path = Path(parsed_file.file_path)
        if str(repo_path) in parsed_file.file_path:
            file_path = Path(parsed_file.file_path).relative_to(repo_path)

        # Skip files inside modules/ directories
        if is_inside_modules_dir(str(file_path)):
            continue

        # Get module directory
        module_dir = str(file_path.parent) if file_path.parent != Path('.') else '.'

        if module_dir not in modules:
            continue

        # Check for backend in parsed data
        parsed_data = parsed_file.parsed_data
        if isinstance(parsed_data, dict):
            backends = parsed_data.get("backends", [])
            if backends:
                modules[module_dir].has_backend = True
                # Get backend type from first backend
                if backends and isinstance(backends[0], dict):
                    modules[module_dir].backend_type = backends[0].get("type")

    return modules


def get_modules_without_backend(modules: dict[str, TerraformModule]) -> list[TerraformModule]:
    """Get list of modules that don't have backend configuration."""
    return [m for m in modules.values() if not m.has_backend]


def format_module_finding(module: TerraformModule) -> dict:
    """Format a module-level finding for reporting."""
    return {
        "module_path": module.module_path,
        "tf_files_count": len(module.tf_files),
        "tf_files": module.tf_files[:3],  # First 3 files for reference
        "has_backend": module.has_backend,
        "backend_type": module.backend_type,
    }
