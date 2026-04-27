"""Webhook processing service with idempotency guarantee."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import WebhookEvent

logger = logging.getLogger(__name__)


class WebhookIdempotencyGuard:
    """
    Guarantees each webhook event is processed exactly once.

    Uses PostgreSQL UNIQUE constraint on (provider, event_id) to prevent duplicates.
    Even if a provider sends the same event 10 times, only the first succeeds.
    """

    async def is_already_processed(
        self, db: AsyncSession, provider: str, event_id: str
    ) -> bool:
        """Check if event was already processed."""
        result = await db.execute(
            select(WebhookEvent).where(
                WebhookEvent.provider == provider,
                WebhookEvent.event_id == event_id,
                WebhookEvent.processed == True,
            )
        )
        return result.scalar_one_or_none() is not None

    async def record_event(
        self,
        db: AsyncSession,
        provider: str,
        event_id: str,
        event_type: str,
        payload: dict,
    ) -> bool:
        """
        Record webhook event. Returns False if duplicate (constraint violation).

        This is the CRITICAL idempotency gate.
        """
        try:
            event = WebhookEvent(
                provider=provider,
                event_id=event_id,
                event_type=event_type,
                payload=payload,
                processed=True,
                processed_at=datetime.now(timezone.utc),
            )
            db.add(event)
            await db.flush()
            return True
        except Exception as e:
            error_str = str(e).lower()
            if "unique" in error_str or "duplicate" in error_str:
                await db.rollback()
                return False
            raise
