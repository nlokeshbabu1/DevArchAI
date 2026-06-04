"""Enterprise audit logging service.

Tracks security-relevant events for compliance and forensics.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session_factory

logger = structlog.get_logger(__name__)


class AuditLogger:
    """Async audit logger that writes to the enterprise_audit_logs table.

    Usage:
        await AuditLogger.log(
            actor_id=user.id,
            org_id=org.id,
            action="user.login",
            resource_type="user",
            resource_id=str(user.id),
            ip_address="192.168.1.1",
            user_agent="Mozilla/...",
        )
    """

    @staticmethod
    async def log(
        actor_id: Optional[str] = None,
        org_id: Optional[str] = None,
        action: str = "unknown",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> None:
        """Write an audit log entry asynchronously."""
        try:
            from app.models.audit_log import AuditLog

            entry = {
                "actor_id": actor_id,
                "org_id": org_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": json.dumps(details) if details else None,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "timestamp": datetime.now(timezone.utc),
            }

            if db is not None:
                db.add(AuditLog(**entry))
            else:
                session_factory = get_session_factory()
                async with session_factory() as session:
                    async with session.begin():
                        session.add(AuditLog(**entry))

            logger.info("Audit log entry", action=action, actor_id=actor_id)

            # Trigger notification service for security-relevant events
            if action.startswith("auth.") or action.startswith("security."):
                try:
                    from app.services.notification import notification_service
                    await notification_service.prepare_notification(
                        action=action,
                        actor_id=actor_id,
                        details=details,
                    )
                except Exception:
                    pass

        except Exception as exc:
            logger.warning("Failed to write audit log", action=action, error=str(exc))


audit_logger = AuditLogger()
