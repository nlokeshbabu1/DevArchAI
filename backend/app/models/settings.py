"""Settings models for user preferences, sessions, and API keys."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserPreference(Base):
    """User notification and preference settings."""

    __tablename__ = "user_preferences"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    email_notifications = Column(Boolean, default=True, nullable=False)
    critical_findings_alerts = Column(Boolean, default=True, nullable=False)
    weekly_reports = Column(Boolean, default=False, nullable=False)
    product_updates = Column(Boolean, default=False, nullable=False)
    scan_completion_alerts = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", backref="preferences", uselist=False)


class UserSession(Base):
    """Active user sessions for device management."""

    __tablename__ = "user_sessions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    refresh_token_hash = Column(String(255), nullable=True)
    device_name = Column(String(255), nullable=True)
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    location = Column(String(255), nullable=True)
    is_current = Column(Boolean, default=False, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)

    last_active_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="sessions")


class ApiKey(Base):
    """API keys for programmatic access."""

    __tablename__ = "api_keys"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=True)
    prefix = Column(String(20), nullable=False)
    key_hash = Column(String(255), nullable=False)
    key_preview = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", backref="api_keys")
