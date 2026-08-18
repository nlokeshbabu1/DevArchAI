"""
GitHub App Authentication Service

Handles JWT generation and installation token exchange for GitHub App authentication.
This service enables the SaaS platform to access user repositories with proper permissions.
"""

import base64
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
import jwt  # PyJWT library
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class GitHubAppToken:
    """Represents a GitHub App installation access token."""
    token: str
    expires_at: datetime
    installation_id: int
    permissions: dict
    repository_selection: str  # "all" or "selected"


class GitHubAppAuthenticationError(Exception):
    """Raised when GitHub App authentication fails."""
    pass


class GitHubAppAuthService:
    """
    Service for GitHub App authentication.
    
    This service:
    1. Generates JWT tokens for GitHub App authentication
    2. Exchanges JWT for installation access tokens
    3. Manages token caching and refresh
    4. Validates installations and permissions
    """

    # GitHub App JWT expiration (max 10 minutes per GitHub docs)
    JWT_EXPIRATION_MINUTES = 9

    # Token cache buffer (refresh 2 minutes before expiry)
    TOKEN_REFRESH_BUFFER_SECONDS = 120

    def __init__(
        self,
        app_id: str | None = None,
        private_key: str | None = None,
    ):
        """
        Initialize GitHub App auth service.
        
        Args:
            app_id: GitHub App ID (from settings if not provided)
            private_key: GitHub App private key in PEM format (from settings if not provided)
        
        Raises:
            GitHubAppAuthenticationError: If app_id or private_key not configured
        """
        self.app_id = app_id or settings.GITHUB_APP_ID
        self.private_key = private_key or settings.GITHUB_APP_PRIVATE_KEY

        if not self.app_id:
            raise GitHubAppAuthenticationError(
                "GitHub App ID not configured. Set GITHUB_APP_ID environment variable."
            )

        if not self.private_key:
            raise GitHubAppAuthenticationError(
                "GitHub App private key not configured. Set GITHUB_APP_PRIVATE_KEY environment variable."
            )

        # Validate private key format (basic check)
        if not self.private_key.startswith("-----BEGIN"):
            logger.warning(
                "GitHub App private key may be invalid (doesn't start with -----BEGIN)",
                key_prefix=self.private_key[:20]
            )

        self._token_cache: dict[int, GitHubAppToken] = {}

    def generate_app_jwt(self) -> str:
        """
        Generate a JWT token for GitHub App authentication.
        
        This JWT is used to authenticate as the GitHub App itself (not as an installation).
        The JWT is valid for 9 minutes (max 10 per GitHub docs).
        
        Returns:
            JWT token string
        
        Raises:
            GitHubAppAuthenticationError: If JWT generation fails
        """
        try:
            # JWT must be issued in the past (handle clock skew)
            now = int(time.time())
            issued_at = now - 60  # 1 minute in the past
            expiration = issued_at + (self.JWT_EXPIRATION_MINUTES * 60)

            payload = {
                "iat": issued_at,  # Issued at
                "exp": expiration,  # Expiration
                "iss": self.app_id,  # Issuer (App ID)
            }

            # Decode private key from base64 if it's base64 encoded
            private_key = self.private_key
            if not private_key.startswith("-----BEGIN"):
                try:
                    # Try to decode as base64
                    private_key = base64.b64decode(private_key).decode('utf-8')
                    logger.info("Decoded base64-encoded private key")
                except Exception:
                    logger.warning("Private key is not base64 encoded, using as-is")

            # Generate JWT with RS256 algorithm
            jwt_token = jwt.encode(
                payload,
                private_key,
                algorithm="RS256"
            )

            logger.info(
                "GitHub App JWT generated successfully",
                app_id=self.app_id,
                expires_in_minutes=self.JWT_EXPIRATION_MINUTES
            )

            return jwt_token

        except Exception as e:
            logger.error("Failed to generate GitHub App JWT", error=str(e))
            raise GitHubAppAuthenticationError(
                f"Failed to generate authentication token: {str(e)}"
            )

    async def get_installation_token(
        self,
        installation_id: int,
        force_refresh: bool = False
    ) -> GitHubAppToken:
        """
        Get or create an installation access token.
        
        Uses token caching to avoid unnecessary API calls.
        Tokens are refreshed automatically when close to expiry.
        
        Args:
            installation_id: GitHub App installation ID for the repository
            force_refresh: Force token refresh even if cached token is valid
        
        Returns:
            GitHubAppToken with access token and metadata
        
        Raises:
            GitHubAppAuthenticationError: If token exchange fails
        """
        # Check cache first
        if not force_refresh and installation_id in self._token_cache:
            cached_token = self._token_cache[installation_id]

            # Check if token is still valid (with refresh buffer)
            now = datetime.now(UTC)
            time_until_expiry = (cached_token.expires_at - now).total_seconds()

            if time_until_expiry > self.TOKEN_REFRESH_BUFFER_SECONDS:
                logger.info(
                    "Using cached installation token",
                    installation_id=installation_id,
                    expires_in_seconds=time_until_expiry
                )
                return cached_token
            else:
                logger.info(
                    "Cached token expiring soon, will refresh",
                    installation_id=installation_id,
                    expires_in_seconds=time_until_expiry
                )

        # Generate app JWT
        app_jwt = self.generate_app_jwt()

        # Exchange JWT for installation token
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                    headers={
                        "Authorization": f"Bearer {app_jwt}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                    timeout=10.0
                )

                if response.status_code == 404:
                    raise GitHubAppAuthenticationError(
                        f"GitHub App installation {installation_id} not found. "
                        "The app may not be installed on this repository. "
                        "Please install the GitHub App first."
                    )

                if response.status_code == 401:
                    raise GitHubAppAuthenticationError(
                        "GitHub App authentication failed. "
                        "The app JWT may be invalid or expired."
                    )

                if response.status_code == 403:
                    error_data = response.json()
                    raise GitHubAppAuthenticationError(
                        f"GitHub App installation access denied: "
                        f"{error_data.get('message', 'Forbidden')}"
                    )

                if response.status_code not in [200, 201]:
                    error_data = response.json()
                    raise GitHubAppAuthenticationError(
                        f"GitHub API error {response.status_code}: "
                        f"{error_data.get('message', 'Unknown error')}"
                    )

                token_data = response.json()

                # Parse token response
                expires_at = datetime.fromisoformat(
                    token_data["expires_at"].replace("Z", "+00:00")
                )

                app_token = GitHubAppToken(
                    token=token_data["token"],
                    expires_at=expires_at,
                    installation_id=installation_id,
                    permissions=token_data.get("permissions", {}),
                    repository_selection=token_data.get("repository_selection", "unknown")
                )

                # Cache the token
                self._token_cache[installation_id] = app_token

                logger.info(
                    "Installation access token obtained",
                    installation_id=installation_id,
                    expires_at=expires_at.isoformat(),
                    permissions=app_token.permissions,
                    repository_selection=app_token.repository_selection
                )

                return app_token

        except httpx.TimeoutException:
            raise GitHubAppAuthenticationError(
                "GitHub API request timed out. Please try again."
            )
        except httpx.RequestError as e:
            raise GitHubAppAuthenticationError(
                f"GitHub API request failed: {str(e)}"
            )
        except GitHubAppAuthenticationError:
            raise
        except Exception as e:
            logger.error("Unexpected error getting installation token", error=str(e))
            raise GitHubAppAuthenticationError(
                f"Failed to get installation token: {str(e)}"
            )

    async def validate_installation(
        self,
        installation_id: int,
        owner: str,
        repo: str
    ) -> dict:
        """
        Validate that a GitHub App installation has access to a specific repository.
        
        Args:
            installation_id: GitHub App installation ID
            owner: Repository owner (user or organization)
            repo: Repository name
        
        Returns:
            Dictionary with installation details and permissions
        
        Raises:
            GitHubAppAuthenticationError: If installation is invalid or inaccessible
        """
        logger.info(
            "Validating GitHub App installation",
            installation_id=installation_id,
            repo=f"{owner}/{repo}"
        )

        # Get installation token
        app_token = await self.get_installation_token(installation_id)

        # Check repository access
        try:
            async with httpx.AsyncClient() as client:
                # Check if app has access to this repository
                response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/installation",
                    headers={
                        "Authorization": f"token {app_token.token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                    timeout=10.0
                )

                if response.status_code == 404:
                    raise GitHubAppAuthenticationError(
                        f"GitHub App is not installed on {owner}/{repo}. "
                        "Please install the app from the repository settings."
                    )

                if response.status_code == 403:
                    raise GitHubAppAuthenticationError(
                        f"GitHub App doesn't have access to {owner}/{repo}. "
                        "Check app permissions and installation."
                    )

                if response.status_code != 200:
                    error_data = response.json()
                    raise GitHubAppAuthenticationError(
                        f"Repository access check failed: {error_data.get('message', 'Unknown error')}"
                    )

                installation_info = response.json()

                logger.info(
                    "Installation validated successfully",
                    installation_id=installation_info["id"],
                    permissions=installation_info.get("permissions", {})
                )

                return {
                    "installation_id": installation_info["id"],
                    "app_id": installation_info["app_id"],
                    "permissions": installation_info.get("permissions", {}),
                    "events": installation_info.get("events", []),
                    "repository_selection": installation_info.get("repository_selection"),
                }

        except httpx.TimeoutException:
            raise GitHubAppAuthenticationError(
                "GitHub API request timed out. Please try again."
            )
        except httpx.RequestError as e:
            raise GitHubAppAuthenticationError(
                f"GitHub API request failed: {str(e)}"
            )
        except GitHubAppAuthenticationError:
            raise
        except Exception as e:
            logger.error("Unexpected error validating installation", error=str(e))
            raise GitHubAppAuthenticationError(
                f"Failed to validate installation: {str(e)}"
            )

    async def get_app_installations(self) -> list[dict]:
        """
        Get all installations of the GitHub App.
        
        Returns:
            List of installation dictionaries
        
        Raises:
            GitHubAppAuthenticationError: If fetching installations fails
        """
        logger.info("Fetching GitHub App installations")

        try:
            # Generate app JWT
            app_jwt = self.generate_app_jwt()

            installations = []
            page = 1

            async with httpx.AsyncClient() as client:
                while True:
                    response = await client.get(
                        "https://api.github.com/app/installations",
                        headers={
                            "Authorization": f"Bearer {app_jwt}",
                            "Accept": "application/vnd.github.v3+json",
                        },
                        params={"per_page": 100, "page": page},
                        timeout=10.0
                    )

                    if response.status_code != 200:
                        error_data = response.json()
                        raise GitHubAppAuthenticationError(
                            f"Failed to fetch installations: {error_data.get('message', 'Unknown error')}"
                        )

                    page_installations = response.json()
                    if not page_installations:
                        break

                    installations.extend(page_installations)
                    page += 1

                logger.info(
                    "Fetched GitHub App installations",
                    count=len(installations)
                )

                return installations

        except Exception as e:
            logger.error("Failed to fetch installations", error=str(e))
            raise GitHubAppAuthenticationError(
                f"Failed to fetch installations: {str(e)}"
            )

    def clear_token_cache(self, installation_id: int | None = None):
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
