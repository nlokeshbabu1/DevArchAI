"""
Abstract base class for all external scanner adapters.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.rule_engine.base import RuleFinding


class BaseScannerAdapter(ABC):
    """Abstract base class for external scanner integration."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable scanner name (e.g. 'Trivy', 'Gitleaks')."""

    @property
    @abstractmethod
    def scanner_id(self) -> str:
        """Unique identifier for this scanner (e.g. 'trivy', 'gitleaks')."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the scanner CLI tool is installed and usable."""

    def get_version(self) -> str | None:
        """Return the installed version of the scanner CLI tool, or None."""
        return None

    @abstractmethod
    def scan(self, repo_path: Path, detection: dict[str, Any]) -> list[RuleFinding]:
        """
        Run the external scanner against the repository path.

        Args:
            repo_path: Path to the cloned repository.
            detection: Technology detection results (DetectedTechnologyStack dict).

        Returns:
            List of normalized RuleFinding objects.
        """

    def get_files_scanned_count(self) -> int | None:
        """Return how many files this scanner processed, or None if unknown."""
        return None

    def get_rules_count(self) -> int | None:
        """Return how many rules/checks this scanner executed, or None."""
        return None

    def get_docker_image(self) -> str | None:
        """
        Return a Docker image that provides this scanner.
        Override if the scanner is available via Docker.
        """
        return None

    def get_install_hint(self) -> str:
        """Return installation instructions for this scanner."""
        return f"Install {self.name}: see {self.name.lower()} documentation"
