"""
Anonymous scan session management.

Allows unauthenticated users to run scans and view limited results.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func

from app.db.base import Base


class AnonymousScan(Base):
    """Anonymous scan session for unauthenticated users."""

    __tablename__ = "anonymous_scans"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_token = Column(String(255), unique=True, index=True, nullable=False)

    # Scan details
    repository_url = Column(String(500), nullable=False)
    repository_name = Column(String(255), nullable=True)
    branch = Column(String(100), default="main", nullable=False)

    # Linked scan ID
    linked_scan_id = Column(String(255), nullable=True)  # UUID of the actual Scan record

    # Results summary (public)
    security_score = Column(String(10), nullable=True)  # e.g., "72/100"
    critical_count = Column(String(10), nullable=True)  # Store as string to allow "2+"
    high_count = Column(String(10), nullable=True)
    medium_count = Column(String(10), nullable=True)
    low_count = Column(String(10), nullable=True)

    # Full results (stored but gated)
    findings_summary = Column(Text, nullable=True)  # JSON string of findings
    ai_suggestions = Column(Text, nullable=True)  # JSON string of AI suggestions (blurred for anon)

    # Status
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)

    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<AnonymousScan(id={self.id}, repository={self.repository_name})>"

    @classmethod
    def generate_session_token(cls) -> str:
        """Generate a unique session token."""
        return f"anon_{uuid.uuid4().hex}"

    @classmethod
    def get_expiry(cls) -> datetime:
        """Get expiration time (24 hours from now)."""
        return datetime.utcnow() + timedelta(hours=24)
