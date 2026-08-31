"""Kubernetes connection model (kubeconfig-based connections)."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class KubernetesConnection(Base):
    """A connected Kubernetes cluster (kubeconfig or AWS EKS managed)."""

    __tablename__ = "kubernetes_connections"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(200), nullable=False)
    provider = Column(String(20), nullable=False, default="kubernetes")
    kind = Column(String(20), nullable=False, default="generic")  # generic | eks
    kubeconfig_encrypted = Column(Text, nullable=True)
    context_name = Column(String(200), nullable=True)
    cluster_endpoint = Column(String(500), nullable=True)
    aws_account_id = Column(String(128), nullable=True)
    aws_region = Column(String(64), nullable=True)
    eks_cluster_name = Column(String(200), nullable=True)
    status = Column(String(20), nullable=False, default="connected")
    is_active = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", backref="kubernetes_connections")
