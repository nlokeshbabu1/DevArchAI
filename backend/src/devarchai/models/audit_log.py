"""Audit log model for compliance."""

import enum
import uuid

from sqlalchemy import (
    JSON as SAJSON,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from devarchai.db.base import Base


class AuditAction(str, enum.Enum):
    """Audit action types."""

    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    API_KEY_CREATE = "api_key_create"
    API_KEY_REVOKE = "api_key_revoke"

    # Organization
    ORG_CREATE = "org_create"
    ORG_UPDATE = "org_update"
    ORG_DELETE = "org_delete"
    MEMBER_INVITE = "member_invite"
    MEMBER_JOIN = "member_join"
    MEMBER_REMOVE = "member_remove"
    MEMBER_ROLE_CHANGE = "member_role_change"

    # Repository
    REPO_ADD = "repo_add"
    REPO_UPDATE = "repo_update"
    REPO_DELETE = "repo_delete"
    REPO_SYNC = "repo_sync"

    # Scan
    SCAN_CREATE = "scan_create"
    SCAN_START = "scan_start"
    SCAN_COMPLETE = "scan_complete"
    SCAN_FAIL = "scan_fail"
    SCAN_CANCEL = "scan_cancel"
    SCAN_DELETE = "scan_delete"

    # Finding
    FINDING_UPDATE = "finding_update"
    FINDING_RESOLVE = "finding_resolve"
    FINDING_REOPEN = "finding_reopen"

    # Report
    REPORT_GENERATE = "report_generate"
    REPORT_DOWNLOAD = "report_download"
    REPORT_SHARE = "report_share"

    # Billing
    SUBSCRIPTION_CREATE = "subscription_create"
    SUBSCRIPTION_UPDATE = "subscription_update"
    SUBSCRIPTION_CANCEL = "subscription_cancel"
    INVOICE_PAID = "invoice_paid"

    # Settings
    SETTINGS_UPDATE = "settings_update"
    INTEGRATION_ADD = "integration_add"
    INTEGRATION_REMOVE = "integration_remove"


class AuditLog(Base):
    """
    Audit log model for tracking all significant actions.

    Used for compliance, debugging, and security analysis.
    """

    __tablename__ = "audit_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Context
    organization_id = Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Action
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(PG_UUID(as_uuid=True), nullable=True)

    # Details
    description = Column(Text, nullable=False)
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(500), nullable=True)
    request_body = Column(SAJSON, nullable=True)
    response_status = Column(Integer, nullable=True)

    # Metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(String(500), nullable=True)
    audit_metadata = Column(SAJSON, nullable=True)  # Renamed from 'metadata' to avoid SQLAlchemy conflict

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    organization = relationship("Organization", back_populates="audit_logs")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "action": self.action.value,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "description": self.description,
            "user_id": str(self.user_id) if self.user_id else None,
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
