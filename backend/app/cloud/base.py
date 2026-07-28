"""Abstract base classes for cloud providers and scanners.

Provides the core data pipeline:
  Scanner -> CloudResourceDTO -> sanitize_json() -> Repository -> PostgreSQL

Every stage has a clear responsibility:
  - Scanner: discovers resources, returns CloudResourceDTO
  - sanitize_json: ensures only JSON-safe types reach DB columns
  - Repository: handles persistence, upsert, batch operations
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# ─── JSON Sanitizer ────────────────────────────────────────────────

# Types that are safe for JSONB columns (PostgreSQL jsonb).
_JSON_SAFE_TYPES = (str, int, float, bool, type(None))


def sanitize_json(value: Any) -> Any:
    """Recursively convert non-JSON-serializable types to JSON-safe equivalents.

    Guarantees the output contains ONLY:
      dict, list, str, int, float, bool, None

    This function is applied to every value before it reaches a JSONB column.
    It does NOT stringify the entire object — it preserves structure and only
    converts the leaf values that PostgreSQL jsonb cannot store natively.

    Supported conversions:
      datetime / date  -> ISO 8601 string (UTC)
      Decimal          -> float
      bytes            -> UTF-8 string (lossy)
      set / tuple      -> list (recursively converted)
      UUID             -> string
      Any unknown obj  -> str(obj) as fallback
    """
    if isinstance(value, _JSON_SAFE_TYPES):
        return value

    # datetime must come before date (datetime is subclass of date)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, set):
        return [sanitize_json(item) for item in sorted(value, key=str)]
    if isinstance(value, tuple):
        return [sanitize_json(item) for item in value]
    if isinstance(value, dict):
        return {k: sanitize_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_json(item) for item in value]
    # bool check before int (bool is subclass of int)
    if isinstance(value, bool):
        return value

    # Fallback: convert unknown types to string representation
    logger.warning("sanitize_json: converting unknown type %s to string", type(value).__name__)
    return str(value)


# ─── Timestamp Normalizer ──────────────────────────────────────────

def normalize_timestamp(value: Any) -> datetime | None:
    """Normalize any timestamp-like value to a timezone-aware UTC datetime.

    Returns None for empty/missing values.

    Handles:
      - datetime (naive or aware) -> UTC-aware datetime
      - date -> datetime at midnight UTC
      - str (ISO 8601) -> parsed datetime
      - None / empty -> None
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt
        except (ValueError, TypeError):
            return None
    return None


# ─── Cloud Resource DTO ────────────────────────────────────────────

class CloudResourceDTO(BaseModel):
    """Pydantic model representing a discovered cloud resource.

    This is the contract between scanners and the persistence layer.
    No raw boto3 objects should ever leave the scanner — they must be
    converted to this DTO before returning.

    Attributes:
        provider: Cloud provider identifier (aws, azure, gcp)
        account_id: AWS account ID or equivalent
        region: AWS region (us-east-1, eu-west-1, etc.)
        service: AWS service name (ec2, s3, iam, rds, etc.)
        resource_id: Unique resource identifier (i-12345, my-bucket, etc.)
        resource_name: Human-readable name
        resource_type: Resource category (instance, volume, bucket, etc.)
        status: Current status (active, stopped, available, etc.)
        tags: Key-value tags (must contain only JSON-safe values)
        configuration: Resource configuration details (must contain only JSON-safe values)
        cost_monthly: Estimated monthly cost in USD
        created_at: When the resource was created (UTC)
        last_modified_at: When the resource was last modified (UTC)
    """

    provider: str
    account_id: str
    region: str
    service: str
    resource_id: str
    resource_name: str
    resource_type: str
    status: str

    tags: dict[str, Any] = Field(default_factory=dict)
    configuration: dict[str, Any] = Field(default_factory=dict)

    cost_monthly: float | None = None
    created_at: datetime | None = None
    last_modified_at: datetime | None = None

    @field_validator("tags", "configuration", mode="before")
    @classmethod
    def sanitize_json_fields(cls, v: Any) -> Any:
        """Ensure JSONB fields contain only safe types."""
        if isinstance(v, dict):
            return sanitize_json(v)
        return v

    @field_validator("created_at", "last_modified_at", mode="before")
    @classmethod
    def normalize_timestamps(cls, v: Any) -> datetime | None:
        """Normalize all timestamps to UTC-aware datetime."""
        return normalize_timestamp(v)


# ─── Legacy Dataclasses (kept for backward compatibility) ───────────
# These dataclasses are used by existing scanners. New code should use
# CloudResourceDTO instead. The orchestrator converts between them.

@dataclass
class CloudResourceData:
    """Normalized resource representation across all cloud providers.

    DEPRECATED: Use CloudResourceDTO instead. This dataclass is kept for
    backward compatibility with existing scanners.
    """
    provider: str
    service: str
    resource_id: str
    resource_name: str
    resource_type: str
    region: str
    status: str
    configuration: dict[str, Any] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)
    cost_monthly: float | None = None
    created_at: datetime | None = None
    last_modified_at: datetime | None = None


@dataclass
class CloudFindingData:
    """Normalized finding representation across all cloud providers."""
    provider: str
    service: str
    category: str  # security, compliance, cost, misconfiguration
    severity: str  # critical, high, medium, low, info
    title: str
    description: str
    resource_id: str | None = None
    resource_type: str | None = None
    region: str = ""
    rule_id: str | None = None
    compliance_frameworks: list[str] = field(default_factory=list)
    remediation: str | None = None
    remediation_url: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class CloudCostData:
    """Normalized cost recommendation."""
    provider: str
    service: str
    title: str
    description: str
    resource_id: str | None = None
    resource_type: str | None = None
    region: str = ""
    monthly_savings: float = 0.0
    current_cost: float = 0.0
    priority: str = "medium"
    category: str = ""
    recommendation_type: str = ""
    estimated_impact: str = ""


class BaseCloudScanner(abc.ABC):
    """Abstract base for a per-service cloud scanner."""

    service_name: str = ""

    @abc.abstractmethod
    async def scan(self, session: Any, regions: list[str]) -> list[CloudResourceData]:
        """Discover and return all resources for this service."""
        ...

    @abc.abstractmethod
    async def check_security(self, session: Any, resources: list[CloudResourceData]) -> list[CloudFindingData]:
        """Analyze security posture for discovered resources."""
        ...

    async def check_cost(self, session: Any, resources: list[CloudResourceData]) -> list[CloudCostData]:
        """Optional: return cost optimization recommendations."""
        return []
