"""
GitHub App Webhook Handler

Processes GitHub App webhook events for:
- Installation creation/deletion
- Installation repository access changes
- Ping events (webhook verification)
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

import structlog
from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.github_installation import GitHubInstallation
from app.models.user import User

logger = structlog.get_logger(__name__)


class GitHubAppWebhookError(Exception):
    """Raised when GitHub App webhook processing fails."""


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Verify GitHub webhook signature.

    Args:
        payload: Raw webhook payload
        signature: X-Hub-Signature-256 header value
        secret: Webhook secret

    Returns:
        True if signature is valid
    """
    if not secret:
        logger.warning("Webhook secret not configured, skipping verification")
        return True

    # GitHub sends signature as "sha256=<hex>"
    if not signature.startswith("sha256="):
        logger.warning("Invalid signature format")
        return False

    expected_signature = signature[7:]  # Remove "sha256=" prefix

    # Calculate HMAC SHA256
    computed_signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed_signature, expected_signature)


class GitHubAppWebhookHandler:
    """
    Handles GitHub App webhook events.

    Processes events related to app installations and repository access.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def handle_webhook(self, request: Request) -> dict[str, Any]:
        """
        Process GitHub App webhook event.

        Args:
            request: FastAPI request object

        Returns:
            Response dictionary

        Raises:
            HTTPException: If webhook verification or processing fails
        """
        # Get headers
        github_event = request.headers.get("X-GitHub-Event", "ping")
        signature = request.headers.get("X-Hub-Signature-256", "")
        delivery_id = request.headers.get("X-GitHub-Delivery", "")

        # Get raw payload
        payload_bytes = await request.body()
        payload = payload_bytes.decode("utf-8")

        # Verify webhook signature
        webhook_secret = settings.GITHUB_APP_WEBHOOK_SECRET
        if not verify_webhook_signature(payload, signature, webhook_secret or ""):
            logger.error("Invalid webhook signature", delivery_id=delivery_id, github_event=github_event)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

        # Parse event data
        import json
        event_data = json.loads(payload)

        logger.info(
            "Received GitHub App webhook event",
            github_event=github_event,
            action=event_data.get("action"),
            delivery_id=delivery_id,
        )

        # Route to appropriate handler
        if github_event == "ping":
            return await self._handle_ping(event_data)
        elif github_event == "installation":
            return await self._handle_installation(event_data)
        elif github_event == "installation_repositories":
            return await self._handle_installation_repositories(event_data)
        else:
            logger.info("Ignoring unsupported event", github_event=github_event)
            return {"status": "ignored", "event": github_event}

    async def _handle_ping(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle ping event (webhook verification).

        GitHub sends this when you first configure a webhook.
        """
        logger.info(
            "Received ping event",
            hook_id=event_data.get("hook_id"),
            zen=event_data.get("zen"),
        )
        return {"status": "ok", "event": "ping"}

    async def _handle_installation(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle installation event.

        Actions:
        - created: App installed on account/repo
        - deleted: App uninstalled from account/repo
        - suspend: Installation suspended
        - unsuspend: Installation resumed
        """
        action = event_data.get("action")
        installation = event_data.get("installation", {})
        installation_id = installation.get("id")
        sender = event_data.get("sender", {})
        sender_login = sender.get("login")

        logger.info(
            "Installation event received",
            action=action,
            installation_id=installation_id,
            sender=sender_login,
        )

        if action == "created":
            return await self._handle_installation_created(event_data)
        elif action == "deleted":
            return await self._handle_installation_deleted(event_data)
        elif action == "suspend":
            return await self._handle_installation_suspended(event_data)
        elif action == "unsuspend":
            return await self._handle_installation_unsuspended(event_data)
        else:
            logger.warning("Unknown installation action", action=action)
            return {"status": "ignored", "action": action}

    async def _handle_installation_created(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle installation created event.

        Stores installation mapping for all repositories the app has access to.
        """
        installation = event_data.get("installation", {})
        installation_id = installation.get("id")
        account = installation.get("account", {})
        account_login = account.get("login")
        repositories = event_data.get("repositories", [])

        logger.info(
            "Installation created",
            installation_id=installation_id,
            account=account_login,
            repository_count=len(repositories),
        )

        # Store installation mappings for each repository
        created_count = 0
        for repo in repositories:
            repo_full_name = repo.get("full_name")
            if not repo_full_name:
                continue

            # Try to find user by GitHub login
            user = await self._find_user_by_github_login(account_login)
            if not user:
                logger.warning(
                    "User not found for installation, skipping repository",
                    github_login=account_login,
                    repo=repo_full_name,
                )
                continue

            # Check if installation mapping already exists
            existing = await self.db.execute(
                select(GitHubInstallation).where(
                    GitHubInstallation.user_id == user.id,
                    GitHubInstallation.repo_full_name == repo_full_name,
                )
            )
            if existing.scalar_one_or_none():
                logger.info(
                    "Installation mapping already exists, skipping",
                    repo=repo_full_name,
                    user_id=str(user.id),
                )
                continue

            # Create installation mapping
            installation_record = GitHubInstallation(
                user_id=user.id,
                repo_full_name=repo_full_name,
                installation_id=installation_id,
            )
            self.db.add(installation_record)
            created_count += 1

            logger.info(
                "Installation mapping created",
                repo=repo_full_name,
                user_id=str(user.id),
                installation_id=installation_id,
            )

        await self.db.commit()

        logger.info(
            "Installation created event processed",
            installation_id=installation_id,
            repositories_processed=created_count,
        )

        return {
            "status": "ok",
            "action": "created",
            "installation_id": installation_id,
            "repositories_processed": created_count,
        }

    async def _handle_installation_deleted(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle installation deleted event.

        Removes installation mappings for all repositories.
        """
        installation = event_data.get("installation", {})
        installation_id = installation.get("id")
        account = installation.get("account", {})
        account_login = account.get("login")

        logger.info(
            "Installation deleted",
            installation_id=installation_id,
            account=account_login,
        )

        # Delete all installation mappings for this installation
        result = await self.db.execute(
            select(GitHubInstallation).where(
                GitHubInstallation.installation_id == installation_id,
            )
        )
        records = result.scalars().all()

        deleted_count = 0
        for record in records:
            await self.db.delete(record)
            deleted_count += 1

        await self.db.commit()

        logger.info(
            "Installation deleted event processed",
            installation_id=installation_id,
            mappings_deleted=deleted_count,
        )

        return {
            "status": "ok",
            "action": "deleted",
            "installation_id": installation_id,
            "mappings_deleted": deleted_count,
        }

    async def _handle_installation_suspended(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle installation suspended event.

        Logs the suspension. Could be extended to disable PR creation for this installation.
        """
        installation = event_data.get("installation", {})
        installation_id = installation.get("id")
        suspension_reason = event_data.get("suspended_by", {}).get("login", "unknown")

        logger.warning(
            "Installation suspended",
            installation_id=installation_id,
            suspended_by=suspension_reason,
        )

        return {
            "status": "ok",
            "action": "suspend",
            "installation_id": installation_id,
        }

    async def _handle_installation_unsuspended(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle installation unsuspended event.
        """
        installation = event_data.get("installation", {})
        installation_id = installation.get("id")

        logger.info(
            "Installation unsuspended",
            installation_id=installation_id,
        )

        return {
            "status": "ok",
            "action": "unsuspend",
            "installation_id": installation_id,
        }

    async def _handle_installation_repositories(
        self, event_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Handle installation_repositories event.

        Actions:
        - added: Repositories added to installation
        - removed: Repositories removed from installation
        """
        action = event_data.get("action")
        installation = event_data.get("installation", {})
        installation_id = installation.get("id")
        account = installation.get("account", {})
        account_login = account.get("login")

        logger.info(
            "Installation repositories event",
            action=action,
            installation_id=installation_id,
            account=account_login,
        )

        if action == "added":
            return await self._handle_repositories_added(event_data)
        elif action == "removed":
            return await self._handle_repositories_removed(event_data)
        else:
            logger.warning("Unknown installation_repositories action", action=action)
            return {"status": "ignored", "action": action}

    async def _handle_repositories_added(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle repositories added to installation.
        """
        installation = event_data.get("installation", {})
        installation_id = installation.get("id")
        account = installation.get("account", {})
        account_login = account.get("login")
        repositories_added = event_data.get("repositories_added", [])

        logger.info(
            "Repositories added to installation",
            installation_id=installation_id,
            account=account_login,
            count=len(repositories_added),
        )

        # Create installation mappings for new repositories
        created_count = 0
        for repo in repositories_added:
            repo_full_name = repo.get("full_name")
            if not repo_full_name:
                continue

            # Find user by GitHub login
            user = await self._find_user_by_github_login(account_login)
            if not user:
                logger.warning(
                    "User not found for repository, skipping",
                    github_login=account_login,
                    repo=repo_full_name,
                )
                continue

            # Check if mapping already exists
            existing = await self.db.execute(
                select(GitHubInstallation).where(
                    GitHubInstallation.user_id == user.id,
                    GitHubInstallation.repo_full_name == repo_full_name,
                )
            )
            if existing.scalar_one_or_none():
                logger.info(
                    "Repository mapping already exists, skipping",
                    repo=repo_full_name,
                )
                continue

            # Create mapping
            installation_record = GitHubInstallation(
                user_id=user.id,
                repo_full_name=repo_full_name,
                installation_id=installation_id,
            )
            self.db.add(installation_record)
            created_count += 1

            logger.info(
                "Repository mapping created",
                repo=repo_full_name,
                user_id=str(user.id),
                installation_id=installation_id,
            )

        await self.db.commit()

        return {
            "status": "ok",
            "action": "added",
            "installation_id": installation_id,
            "repositories_processed": created_count,
        }

    async def _handle_repositories_removed(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle repositories removed from installation.
        """
        installation = event_data.get("installation", {})
        installation_id = installation.get("id")
        repositories_removed = event_data.get("repositories_removed", [])

        logger.info(
            "Repositories removed from installation",
            installation_id=installation_id,
            count=len(repositories_removed),
        )

        # Remove installation mappings
        deleted_count = 0
        for repo in repositories_removed:
            repo_full_name = repo.get("full_name")
            if not repo_full_name:
                continue

            result = await self.db.execute(
                select(GitHubInstallation).where(
                    GitHubInstallation.installation_id == installation_id,
                    GitHubInstallation.repo_full_name == repo_full_name,
                )
            )
            record = result.scalar_one_or_none()
            if record:
                await self.db.delete(record)
                deleted_count += 1

        await self.db.commit()

        return {
            "status": "ok",
            "action": "removed",
            "installation_id": installation_id,
            "mappings_deleted": deleted_count,
        }

    async def _find_user_by_github_login(self, github_login: str) -> User | None:
        """
        Find a user by their GitHub login.

        Args:
            github_login: GitHub username/login

        Returns:
            User object if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.github_login == github_login)
        )
        return result.scalar_one_or_none()
