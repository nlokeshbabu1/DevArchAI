"""
GitHub URL Validator Service
Validates GitHub repository URLs and extracts owner/repo information.
"""

import re
from typing import Optional
from dataclasses import dataclass
import structlog

from app.core.exceptions import InvalidRepositoryException

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of GitHub URL validation."""

    valid: bool
    owner: str = ""
    repo: str = ""
    error_message: str = ""


class GitHubValidator:
    """Service for validating GitHub repository URLs."""

    # GitHub URL patterns
    GITHUB_URL_PATTERN = re.compile(
        r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
        re.IGNORECASE
    )

    def validate_github_repo(self, url: str) -> ValidationResult:
        """
        Validate a GitHub repository URL.

        Args:
            url: The GitHub repository URL to validate

        Returns:
            ValidationResult with valid status and extracted owner/repo

        Examples:
            >>> validator = GitHubValidator()
            >>> result = validator.validate_github_repo("https://github.com/torvalds/linux")
            >>> result.valid
            True
            >>> result.owner
            'torvalds'
            >>> result.repo
            'linux'
        """
        # Check if URL is empty
        if not url or not url.strip():
            return ValidationResult(
                valid=False,
                error_message="URL cannot be empty"
            )

        url = url.strip()

        # Check if URL starts with https://github.com/
        if not url.startswith("https://github.com/"):
            if url.startswith("http://github.com/"):
                return ValidationResult(
                    valid=False,
                    error_message="URL must use HTTPS. Please use https://github.com/..."
                )
            if url.startswith("git@"):
                return ValidationResult(
                    valid=False,
                    error_message="SSH URLs are not supported. Please use HTTPS URL format."
                )
            if "github.com" in url:
                return ValidationResult(
                    valid=False,
                    error_message="Invalid URL format. Please use: https://github.com/owner/repository"
                )
            return ValidationResult(
                valid=False,
                error_message="URL must start with https://github.com/"
            )

        # Parse URL to extract owner and repository
        match = self.GITHUB_URL_PATTERN.match(url)

        if not match:
            return ValidationResult(
                valid=False,
                error_message="Invalid repository URL format. Expected: https://github.com/owner/repository"
            )

        owner = match.group(1)
        repo = match.group(2)

        # Validate owner name
        if not self._is_valid_github_name(owner):
            return ValidationResult(
                valid=False,
                error_message=f"Invalid owner name: '{owner}'. GitHub names must be 1-39 characters."
            )

        # Validate repository name
        if not self._is_valid_github_name(repo):
            return ValidationResult(
                valid=False,
                error_message=f"Invalid repository name: '{repo}'."
            )

        logger.info(
            "GitHub URL validated successfully",
            owner=owner,
            repo=repo
        )

        return ValidationResult(
            valid=True,
            owner=owner,
            repo=repo
        )

    def _is_valid_github_name(self, name: str) -> bool:
        """
        Validate GitHub username or repository name.

        GitHub rules:
        - 1-39 characters for usernames
        - Repository names can be up to 100 characters
        - Can contain letters, numbers, hyphens, underscores, dots
        - Cannot start or end with hyphen or dot
        """
        if not name:
            return False

        # Length check (conservative limit)
        if len(name) > 100:
            return False

        # Pattern: alphanumeric, hyphens, underscores, dots
        # Cannot start/end with hyphen or dot
        pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9._-]{0,98}[a-zA-Z0-9])?$"

        # Allow single character names
        if len(name) == 1:
            pattern = r"^[a-zA-Z0-9]$"

        return bool(re.match(pattern, name))

    def normalize_url(self, url: str) -> str:
        """
        Normalize a GitHub URL to standard format.

        Args:
            url: GitHub URL to normalize

        Returns:
            Normalized URL in format: https://github.com/owner/repository
        """
        result = self.validate_github_repo(url)

        if not result.valid:
            raise InvalidRepositoryException(f"Invalid GitHub URL: {result.error_message}")

        return f"https://github.com/{result.owner}/{result.repo}"

    def get_full_name(self, url: str) -> str:
        """
        Get the full repository name (owner/repo) from URL.

        Args:
            url: GitHub repository URL

        Returns:
            Full name in format: owner/repository
        """
        result = self.validate_github_repo(url)

        if not result.valid:
            raise InvalidRepositoryException(f"Invalid GitHub URL: {result.error_message}")

        return f"{result.owner}/{result.repo}"


# Singleton instance for convenience
_validator = GitHubValidator()


def validate_github_repo(url: str) -> ValidationResult:
    """
    Convenience function to validate a GitHub repository URL.

    Args:
        url: GitHub repository URL to validate

    Returns:
        ValidationResult with validation status and extracted info
    """
    return _validator.validate_github_repo(url)


def get_full_name(url: str) -> str:
    """
    Convenience function to get full repository name from URL.

    Args:
        url: GitHub repository URL

    Returns:
        Full name in format: owner/repository
    """
    return _validator.get_full_name(url)
