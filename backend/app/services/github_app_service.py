"""GitHub App service for JWT and installation tokens."""

from __future__ import annotations

import base64
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import jwt
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class GitHubAppServiceError(Exception):
    """Raised when GitHub App authentication fails."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class GitHubAppToken:
    """Represents a GitHub App installation access token."""

    def __init__(
        self,
        token: str,
        expires_at: datetime,
        installation_id: int,
        permissions: dict | None = None,
        repository_selection: str = "unknown",
    ):
        self.token = token
        self.expires_at = expires_at
        self.installation_id = installation_id
        self.permissions = permissions or {}
        self.repository_selection = repository_selection

    @property
    def is_expired(self) -> bool:
        """Check if token is expired or expiring soon."""
        if not self.expires_at:
            return True
        # Consider token expired 2 minutes before actual expiry for safety margin
        expiry_with_buffer = self.expires_at - timedelta(minutes=2)
        return datetime.now(timezone.utc) > expiry_with_buffer

    @property
    def time_until_expiry(self) -> float:
        """Get seconds until token expires."""
        if not self.expires_at:
            return 0
        return (self.expires_at - datetime.now(timezone.utc)).total_seconds()


class GitHubAppService:
    """Service for GitHub App JWT and installation token generation."""

    # JWT expiration (max 10 minutes per GitHub docs, using 9 for safety)
    JWT_EXPIRATION_MINUTES = 9

    # Token cache buffer (refresh 2 minutes before expiry)
    TOKEN_REFRESH_BUFFER_SECONDS = 120

    def __init__(
        self,
        app_id: str | None = None,
        private_key: str | None = None,
    ):
        self.app_id = app_id or settings.GITHUB_APP_ID
        self.private_key = private_key or settings.GITHUB_APP_PRIVATE_KEY

        # Try to load from file if not provided directly
        if not self.private_key and settings.GITHUB_APP_PRIVATE_KEY_PATH:
            key_path = Path(settings.GITHUB_APP_PRIVATE_KEY_PATH)
            if key_path.exists():
                self.private_key = key_path.read_text(encoding="utf-8")
                logger.info("Loaded GitHub App private key from file", path=str(key_path))

        if not self.app_id:
            raise GitHubAppServiceError(
                "Missing GitHub App ID configuration. Set GITHUB_APP_ID environment variable."
            )
        if not self.private_key:
            raise GitHubAppServiceError(
                "Missing GitHub App private key configuration. "
                "Set GITHUB_APP_PRIVATE_KEY or GITHUB_APP_PRIVATE_KEY_PATH environment variable."
            )

        # Validate private key format (basic check)
        if not self.private_key.strip().startswith("-----BEGIN"):
            logger.warning(
                "GitHub App private key may be invalid (doesn't start with -----BEGIN RSA PRIVATE KEY-----)",
                key_prefix=self.private_key[:20],
            )

        # Token cache: installation_id -> GitHubAppToken
        self._token_cache: dict[int, GitHubAppToken] = {}

    async def get_installation_id(self, owner: str, repo: str) -> int:
        """
        Helper to fetch installation_id for a given repository.

        This uses the GitHub App JWT flow and calls the GitHub API:
        GET /repos/{owner}/{repo}/installation
        """
        logger.info(
            "Fetching installation_id from GitHub API",
            owner=owner,
            repo=repo,
        )

        installation_id = await self.get_installation_for_repo(owner=owner, repo=repo)

        logger.info(
            "Installation found: {installation_id}",
            installation_id=installation_id,
        )
        logger.info(
            "Using installation_id for repo: {owner}/{repo}",
            owner=owner,
            repo=repo,
            installation_id=installation_id,
        )

        return installation_id

    def _decode_private_key(self, private_key: str) -> str:
        """
        Decode private key from base64 if it's base64 encoded.

        GitHub App private keys can be provided as:
        1. Raw PEM format
        2. Base64-encoded PEM (for environment variables)
        """
        # If it already looks like a PEM key, use as-is
        if private_key.strip().startswith("-----BEGIN"):
            return private_key

        # Try to decode as base64
        try:
            decoded = base64.b64decode(private_key).decode("utf-8")
            if decoded.startswith("-----BEGIN"):
                logger.info("Successfully decoded base64-encoded private key")
                return decoded
        except Exception:
            pass

        # Return as-is if not base64
        logger.warning("Private key doesn't appear to be base64 or PEM format, using as-is")
        return private_key

    def generate_jwt(self, app_id: str | None = None, private_key: str | None = None) -> str:
        """
        Generate GitHub App JWT using RS256.

        JWT is valid for at most 10 minutes (we use 9 minutes).
        The issued-at time is set 60 seconds in the past to handle clock skew.

        Args:
            app_id: GitHub App ID (uses instance default if not provided)
            private_key: PEM private key (uses instance default if not provided)

        Returns:
            JWT token string

        Raises:
            GitHubAppServiceError: If JWT generation fails
        """
        resolved_app_id = app_id or self.app_id
        resolved_private_key = private_key or self.private_key

        if not resolved_app_id or not resolved_private_key:
            raise GitHubAppServiceError("Missing GitHub App credentials for JWT generation")

        # Decode private key if base64 encoded
        decoded_private_key = self._decode_private_key(resolved_private_key)

        logger.info("Generating GitHub App JWT", app_id=resolved_app_id)

        now = int(time.time())
        payload = {
            "iat": now - 60,  # Issued 1 minute ago (handle clock skew)
            "exp": now + (self.JWT_EXPIRATION_MINUTES * 60),  # Expires in 9 minutes
            "iss": str(resolved_app_id),  # Issuer (App ID)
        }

        try:
            token = jwt.encode(payload, decoded_private_key, algorithm="RS256")
            logger.debug("JWT generated successfully", expires_in_minutes=self.JWT_EXPIRATION_MINUTES)
            return token
        except Exception as exc:
            logger.error("Failed to generate GitHub App JWT", error=str(exc))
            raise GitHubAppServiceError(f"Failed to generate GitHub App JWT: {exc}") from exc

    async def get_installation_token(
        self,
        installation_id: int,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """
        Exchange GitHub App JWT for an installation access token.

        Uses token caching to avoid unnecessary API calls.
        Tokens are refreshed automatically when close to expiry.

        Args:
            installation_id: GitHub App installation ID
            force_refresh: Force token refresh even if cached token is valid

        Returns:
            Dictionary with token and metadata:
            - token: str (installation access token)
            - expires_at: datetime
            - permissions: dict
            - repository_selection: str

        Raises:
            GitHubAppServiceError: If token exchange fails
        """
        # Check cache first
        if not force_refresh and installation_id in self._token_cache:
            cached_token = self._token_cache[installation_id]

            # Check if token is still valid (with refresh buffer)
            if cached_token.time_until_expiry > self.TOKEN_REFRESH_BUFFER_SECONDS:
                logger.info(
                    "Using cached installation token",
                    installation_id=installation_id,
                    expires_in_seconds=cached_token.time_until_expiry,
                )
                return {
                    "token": cached_token.token,
                    "expires_at": cached_token.expires_at.isoformat(),
                    "permissions": cached_token.permissions,
                    "repository_selection": cached_token.repository_selection,
                }
            else:
                logger.info(
                    "Cached token expiring soon, will refresh",
                    installation_id=installation_id,
                    expires_in_seconds=cached_token.time_until_expiry,
                )

        # Generate app JWT
        app_jwt = self.generate_jwt()

        # Exchange JWT for installation token
        url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=headers)

        except httpx.RequestError as exc:
            logger.error("Installation token request failed", error=str(exc))
            raise GitHubAppServiceError(f"Failed to reach GitHub API: {exc}") from exc

        # Handle error responses
        if response.status_code == 404:
            error_msg = (
                f"GitHub App installation {installation_id} not found. "
                "The app may not be installed on this repository. "
                "Please install the GitHub App first."
            )
            logger.error(error_msg)
            raise GitHubAppServiceError(error_msg, status_code=404)

        if response.status_code == 401:
            error_msg = (
                "GitHub App authentication failed. "
                "The app JWT may be invalid or expired. "
                "Check your App ID and private key configuration."
            )
            logger.error(error_msg)
            raise GitHubAppServiceError(error_msg, status_code=401)

        if response.status_code == 403:
            error_msg = (
                f"GitHub App installation access denied. "
                f"Installation ID: {installation_id}. "
                "Check app permissions and installation status."
            )
            logger.error(error_msg, detail=response.text)
            raise GitHubAppServiceError(error_msg, status_code=403)

        if response.status_code not in (200, 201):
            logger.error(
                "Installation token exchange failed",
                installation_id=installation_id,
                status_code=response.status_code,
                detail=response.text,
            )
            raise GitHubAppServiceError(
                f"Failed to fetch installation token (status {response.status_code})"
            )

        # Parse successful response
        data = response.json()
        if not data.get("token"):
            raise GitHubAppServiceError("GitHub API did not return installation token")

        # Parse expiry time
        expires_at = datetime.fromisoformat(
            data["expires_at"].replace("Z", "+00:00")
        )

        # Create token object
        app_token = GitHubAppToken(
            token=data["token"],
            expires_at=expires_at,
            installation_id=installation_id,
            permissions=data.get("permissions", {}),
            repository_selection=data.get("repository_selection", "unknown"),
        )

        # Cache the token
        self._token_cache[installation_id] = app_token

        logger.info(
            "Installation access token obtained",
            installation_id=installation_id,
            expires_at=expires_at.isoformat(),
            permissions=app_token.permissions,
            repository_selection=app_token.repository_selection,
        )

        return {
            "token": app_token.token,
            "expires_at": app_token.expires_at.isoformat(),
            "permissions": app_token.permissions,
            "repository_selection": app_token.repository_selection,
        }

    async def get_installation_for_repo(
        self,
        owner: str,
        repo: str,
    ) -> int:
        """
        Dynamically fetch the GitHub App installation ID for a repository.

        This queries the GitHub API directly to find which installation
        has access to the specified repository, providing a fallback
        when the database doesn't have a record.

        Args:
            owner: Repository owner (user or organization)
            repo: Repository name

        Returns:
            Installation ID (integer)

        Raises:
            GitHubAppServiceError: If no installation is found
        """
        logger.info(
            "Fetching installation for repository",
            owner=owner,
            repo=repo,
        )

        try:
            app_jwt = self.generate_jwt()

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/installation",
                    headers={
                        "Authorization": f"Bearer {app_jwt}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    timeout=15.0,
                )

                if response.status_code == 404:
                    raise GitHubAppServiceError(
                        f"GitHub App is not installed on {owner}/{repo}. "
                        "Please install the GitHub App from the repository settings.",
                        status_code=404,
                    )

                if response.status_code == 403:
                    raise GitHubAppServiceError(
                        f"GitHub App doesn't have access to {owner}/{repo}. "
                        "Check app permissions and installation status.",
                        status_code=403,
                    )

                if response.status_code != 200:
                    raise GitHubAppServiceError(
                        f"Failed to fetch installation info: {response.status_code}",
                        status_code=response.status_code,
                    )

                installation_data = response.json()
                installation_id = installation_data["id"]

                logger.info(
                    "Installation found via GitHub API",
                    owner=owner,
                    repo=repo,
                    installation_id=installation_id,
                    repository_selection=installation_data.get("repository_selection"),
                )

                return installation_id

        except GitHubAppServiceError:
            raise
        except httpx.TimeoutException:
            raise GitHubAppServiceError(
                "GitHub API request timed out. Please try again.",
                status_code=504,
            )
        except httpx.RequestError as exc:
            raise GitHubAppServiceError(
                f"GitHub API request failed: {exc}",
                status_code=502,
            )
        except Exception as exc:
            logger.error("Unexpected error fetching installation", error=str(exc))
            raise GitHubAppServiceError(
                f"Failed to fetch installation info: {exc}",
                status_code=500,
            )

    async def get_app_installations(self) -> list[dict[str, Any]]:
        """
        Get all installations of the GitHub App.

        Returns:
            List of installation dictionaries with:
            - id: installation ID
            - account: account info (login, type)
            - repository_selection: "all" or "selected"
            - repositories_url: URL to list repositories

        Raises:
            GitHubAppServiceError: If fetching installations fails
        """
        logger.info("Fetching GitHub App installations")

        try:
            app_jwt = self.generate_jwt()
            installations = []
            page = 1

            async with httpx.AsyncClient() as client:
                while True:
                    response = await client.get(
                        "https://api.github.com/app/installations",
                        headers={
                            "Authorization": f"Bearer {app_jwt}",
                            "Accept": "application/vnd.github+json",
                            "X-GitHub-Api-Version": "2022-11-28",
                        },
                        params={"per_page": 100, "page": page},
                        timeout=15.0,
                    )

                    if response.status_code != 200:
                        raise GitHubAppServiceError(
                            f"Failed to fetch installations: {response.status_code}"
                        )

                    page_installations = response.json()
                    if not page_installations:
                        break

                    installations.extend(page_installations)
                    page += 1

            logger.info("Fetched GitHub App installations", count=len(installations))
            return installations

        except GitHubAppServiceError:
            raise
        except Exception as exc:
            logger.error("Failed to fetch installations", error=str(exc))
            raise GitHubAppServiceError(f"Failed to fetch installations: {exc}") from exc

    async def validate_installation(
        self,
        installation_id: int,
        owner: str,
        repo: str,
    ) -> dict[str, Any]:
        """
        Validate that a GitHub App installation has access to a specific repository.

        Args:
            installation_id: GitHub App installation ID
            owner: Repository owner (user or organization)
            repo: Repository name

        Returns:
            Dictionary with installation details and permissions

        Raises:
            GitHubAppServiceError: If installation is invalid or inaccessible
        """
        logger.info(
            "Validating GitHub App installation",
            installation_id=installation_id,
            repo=f"{owner}/{repo}",
        )

        # Get installation token
        token_data = await self.get_installation_token(installation_id)
        installation_token = token_data["token"]

        # Check repository access
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/installation",
                    headers={
                        "Authorization": f"token {installation_token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    timeout=10.0,
                )

                if response.status_code == 404:
                    raise GitHubAppServiceError(
                        f"GitHub App is not installed on {owner}/{repo}. "
                        "Please install the app from the repository settings.",
                        status_code=404,
                    )

                if response.status_code == 403:
                    raise GitHubAppServiceError(
                        f"GitHub App doesn't have access to {owner}/{repo}. "
                        "Check app permissions and installation.",
                        status_code=403,
                    )

                if response.status_code != 200:
                    raise GitHubAppServiceError(
                        f"Repository access check failed: {response.status_code}",
                        status_code=response.status_code,
                    )

                installation_info = response.json()
                logger.info(
                    "Installation validated successfully",
                    installation_id=installation_info["id"],
                    permissions=installation_info.get("permissions", {}),
                )

                return {
                    "installation_id": installation_info["id"],
                    "app_id": installation_info["app_id"],
                    "permissions": installation_info.get("permissions", {}),
                    "events": installation_info.get("events", []),
                    "repository_selection": installation_info.get("repository_selection"),
                }

        except GitHubAppServiceError:
            raise
        except Exception as exc:
            logger.error("Unexpected error validating installation", error=str(exc))
            raise GitHubAppServiceError(f"Failed to validate installation: {exc}") from exc

    def clear_token_cache(self, installation_id: int | None = None) -> None:
        """
        Clear cached installation tokens.

        Args:
            installation_id: Specific installation to clear, or None to clear all
        """
        if installation_id:
            self._token_cache.pop(installation_id, None)
            logger.info("Cleared token cache for installation", installation_id=installation_id)
        else:
            self._token_cache.clear()
            logger.info("Cleared all token caches")

    def detect_token_type(self, token: str) -> str:
        """
        Detect the type of GitHub token based on its format.

        Returns:
            Token type: 'github_app', 'oauth', 'pat', or 'unknown'
        """
        # GitHub App installation tokens start with 'ghs_'
        if token.startswith("ghs_"):
            return "github_app"
        # OAuth tokens start with 'gho_'
        if token.startswith("gho_"):
            return "oauth"
        # Personal Access Tokens (classic) don't have a prefix but are 40+ chars
        if len(token) >= 40:
            return "pat"
        return "unknown"

