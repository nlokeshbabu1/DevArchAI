"""Model mixins for common fields."""

from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func
import uuid
from uuid import UUID as UUIDType


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""

    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    is_deleted = Column(
        DateTime(timezone=True),
        nullable=False,
        default=False,
        index=True,
    )


class UUIDPrimaryKeyMixin:
    """Mixin for UUID primary key."""

    id = Column(
        UUIDType(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )


class OrganizationMixin:
    """Mixin for organization-based multi-tenancy."""

    organization_id = Column(
        UUIDType(as_uuid=True),
        nullable=False,
        index=True,
    )
