"""Notification service for security alerts.

This is a stub/preparation interface for future email/SMS notification delivery.
No actual sending is implemented yet.
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class NotificationService:

    @staticmethod
    async def prepare_notification(
        action: str,
        actor_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Prepare a notification for security-relevant events.

        This method logs the intent to notify. Actual email/SMS delivery
        will be implemented when the notification provider is configured.

        Currently supported event types:
        - auth.new_device_login
        - auth.login.failed (repeated)
        - auth.login.success (from new location)
        - security.*
        """
        if action in ("auth.new_device_login",):
            logger.info(
                "Security alert: new device login detected",
                action=action,
                actor_id=actor_id,
                details=details,
            )
        elif action.startswith("auth.login.failed"):
            logger.info(
                "Security alert: failed login attempt",
                action=action,
                actor_id=actor_id,
                details=details,
            )


notification_service = NotificationService()
