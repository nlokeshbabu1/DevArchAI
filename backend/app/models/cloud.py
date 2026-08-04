"""Cloud Integration models — multi-cloud support."""

from __future__ import annotations

import enum
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class CloudProvider(str, enum.Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    ORACLE = "oracle"


class ConnectionStatus(str, enum.Enum):
    CONNECTED = "connected"
    SCANNING = "scanning"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class ScanStatus(str, enum.Enum):
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CloudConnection(Base):
    __tablename__ = "cloud_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(String(20), nullable=False, index=True)
    account_id = Column(String(128), nullable=False)
    connection_name = Column(String(100), nullable=False, server_default=text("''"))
    role_arn = Column(Text, nullable=False)
    external_id_encrypted = Column(Text, nullable=True)
    regions = Column(JSONB, nullable=False, server_default=text("'[\"us-east-1\"]'::jsonb"))
    status = Column(String(20), nullable=False, server_default=text("'connected'"))
    scan_status = Column(String(20), nullable=False, server_default=text("'idle'"))
    scan_progress = Column(Float, nullable=False, server_default=text("0"))
    resource_count = Column(Integer, nullable=False, server_default=text("0"))
    finding_count = Column(Integer, nullable=False, server_default=text("0"))
    security_score = Column(Float, nullable=True)
    estimated_monthly_cost = Column(Float, nullable=True, server_default=text("0"))
    last_scanned_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    resources = relationship(
        "CloudResource", back_populates="connection", cascade="all, delete-orphan"
    )
    findings = relationship(
        "CloudFinding", back_populates="connection", cascade="all, delete-orphan"
    )
    cost_recommendations = relationship(
        "CloudCostRecommendation", back_populates="connection", cascade="all, delete-orphan"
    )
    scan_sessions = relationship(
        "CloudScanSession", back_populates="connection", cascade="all, delete-orphan"
    )
    compliance_results = relationship(
        "CloudComplianceResult", back_populates="connection", cascade="all, delete-orphan"
    )
    ai_recommendations = relationship(
        "AIRecommendation", back_populates="connection", cascade="all, delete-orphan"
    )


class CloudScanSession(Base):
    __tablename__ = "cloud_scan_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cloud_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(20), nullable=False, server_default=text("'queued'"))
    progress = Column(Float, nullable=False, server_default=text("0"))
    current_stage = Column(String(100), nullable=False, server_default=text("''"))
    stages_completed = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    stages_total = Column(Integer, nullable=False, server_default=text("0"))
    resources_scanned = Column(Integer, nullable=False, server_default=text("0"))
    findings_count = Column(Integer, nullable=False, server_default=text("0"))
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    connection = relationship("CloudConnection", back_populates="scan_sessions")


class CloudResource(Base):
    __tablename__ = "cloud_resources"
    __table_args__ = (
        # Unique constraint for upsert: (connection_id, provider, region, resource_id)
        # This prevents duplicate resources across scans.
        # Added via migration 026_cloud_resources_unique_constraint.py
        # Kept here for Alembic autogenerate detection and documentation.
        UniqueConstraint(
            "connection_id", "provider", "region", "resource_id",
            name="uq_cloud_resources_conn_provider_region_resource",
        ),
        {"comment": "Cloud resources discovered by scanners"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cloud_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(String(20), nullable=False)
    account_id = Column(String(128), nullable=False, server_default=text("''"))
    service = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(512), nullable=False)
    resource_name = Column(String(512), nullable=False, server_default=text("''"))
    resource_type = Column(String(100), nullable=False)
    region = Column(String(30), nullable=False, index=True)
    status = Column(String(30), nullable=False, server_default=text("'active'"))
    configuration = Column(JSONB, nullable=True)
    tags = Column(JSONB, nullable=True)
    cost_monthly = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    last_modified_at = Column(DateTime(timezone=True), nullable=True)
    scanned_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_scan_id = Column(String(64), nullable=True, index=True)

    connection = relationship("CloudConnection", back_populates="resources")


class CloudFinding(Base):
    __tablename__ = "cloud_findings"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "provider", "service", "region", "resource_id", "rule_id",
            name="uq_cloud_findings_conn_prov_svc_region_res_rule",
        ),
        {"comment": "Security findings discovered by cloud scanners"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cloud_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(String(20), nullable=False)
    service = Column(String(50), nullable=False, index=True)
    category = Column(String(30), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False, server_default=text("''"))
    resource_id = Column(String(512), nullable=False, server_default=text("''"))
    resource_type = Column(String(100), nullable=True)
    region = Column(String(30), nullable=False)
    rule_id = Column(String(100), nullable=False, server_default=text("''"))
    compliance_frameworks = Column(JSONB, nullable=True)
    remediation = Column(Text, nullable=True)
    remediation_url = Column(String(1000), nullable=True)
    evidence = Column(JSONB, nullable=True)
    status = Column(String(20), nullable=False, server_default=text("'open'"))
    last_scan_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    connection = relationship("CloudConnection", back_populates="findings")


class CloudCostRecommendation(Base):
    __tablename__ = "cloud_cost_recommendations"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "provider", "service", "region", "resource_id", "recommendation_type",
            name="uq_cloud_costs_conn_prov_svc_region_res_type",
        ),
        {"comment": "Cost optimization recommendations from cloud scanners"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cloud_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(String(20), nullable=False)
    service = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False, server_default=text("''"))
    resource_id = Column(String(512), nullable=False, server_default=text("''"))
    resource_type = Column(String(100), nullable=True)
    region = Column(String(30), nullable=False)
    monthly_savings = Column(Float, nullable=False, server_default=text("0"))
    current_cost = Column(Float, nullable=False, server_default=text("0"))
    priority = Column(String(20), nullable=False, server_default=text("'medium'"))
    category = Column(String(50), nullable=False)
    recommendation_type = Column(String(100), nullable=False)
    estimated_impact = Column(String(200), nullable=False, server_default=text("''"))
    status = Column(String(20), nullable=False, server_default=text("'open'"))
    last_scan_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    connection = relationship("CloudConnection", back_populates="cost_recommendations")


class CloudComplianceResult(Base):
    __tablename__ = "cloud_compliance_results"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "provider", "framework",
            name="uq_cloud_compliance_conn_prov_framework",
        ),
        {"comment": "Compliance framework scores from cloud scanners"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cloud_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    framework = Column(String(50), nullable=False)
    total_controls = Column(Integer, nullable=False, server_default=text("0"))
    passed = Column(Integer, nullable=False, server_default=text("0"))
    failed = Column(Integer, nullable=False, server_default=text("0"))
    warnings = Column(Integer, nullable=False, server_default=text("0"))
    not_applicable = Column(Integer, nullable=False, server_default=text("0"))
    score = Column(Float, nullable=False, server_default=text("0"))
    provider = Column(String(20), nullable=False, server_default=text("'aws'"))
    status = Column(String(20), nullable=False, server_default=text("'active'"))
    last_scan_id = Column(String(64), nullable=True, index=True)
    last_checked = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    connection = relationship("CloudConnection", back_populates="compliance_results")
