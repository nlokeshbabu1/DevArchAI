"""AWS account, inventory, finding, and cost recommendation models."""

import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class AWSAccount(Base):
    """Connected AWS account with encrypted credentials."""

    __tablename__ = "aws_accounts"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(String(32), nullable=False, index=True)
    account_alias = Column(String(255), nullable=True)
    connection_type = Column(String(32), default="access_key", nullable=False)
    access_key_id_encrypted = Column(Text, nullable=True)
    secret_access_key_encrypted = Column(Text, nullable=True)
    role_arn_encrypted = Column(Text, nullable=True)
    external_id_encrypted = Column(Text, nullable=True)
    default_region = Column(String(32), default="us-east-1", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    scan_status = Column(String(32), default="pending", nullable=False)
    scan_progress = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    last_scanned_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", backref="aws_accounts")
    inventory = relationship("AWSInventory", back_populates="account", cascade="all, delete-orphan")
    findings = relationship("AWSFinding", back_populates="account", cascade="all, delete-orphan")
    cost_recommendations = relationship("AWSCostRecommendation", back_populates="account", cascade="all, delete-orphan")


class AWSInventory(Base):
    """Summarized AWS resource metadata."""

    __tablename__ = "aws_inventory"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    account_id = Column(PG_UUID(as_uuid=True), ForeignKey("aws_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_type = Column(String(64), nullable=False, index=True)
    resource_id = Column(String(512), nullable=False, index=True)
    name = Column(String(512), nullable=True)
    region = Column(String(64), nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    account = relationship("AWSAccount", back_populates="inventory")


class AWSFinding(Base):
    """AWS security and IAM finding."""

    __tablename__ = "aws_findings"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    account_id = Column(PG_UUID(as_uuid=True), ForeignKey("aws_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(64), nullable=False, index=True)
    severity = Column(String(16), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    resource_type = Column(String(64), nullable=True)
    resource_id = Column(String(512), nullable=True)
    region = Column(String(64), nullable=True)
    recommendation = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    account = relationship("AWSAccount", back_populates="findings")


class AWSCostRecommendation(Base):
    """AWS cost optimization recommendation."""

    __tablename__ = "aws_cost_recommendations"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    account_id = Column(PG_UUID(as_uuid=True), ForeignKey("aws_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_type = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    resource_type = Column(String(64), nullable=True)
    resource_id = Column(String(512), nullable=True)
    region = Column(String(64), nullable=True)
    estimated_monthly_savings = Column(Float, default=0.0, nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    account = relationship("AWSAccount", back_populates="cost_recommendations")
