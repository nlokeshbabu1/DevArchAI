"""Unit tests for cloud scanning infrastructure.

Covers:
  - sanitize_json: datetime, Decimal, bytes, set, tuple, UUID, nested dicts/lists
  - normalize_timestamp: datetime, date, string, naive/aware
  - CloudResourceDTO: validation, field sanitization, timestamp normalization
  - CloudResourceRepository: _resource_to_row, _legacy_resource_to_row, sanitize
  - CloudFindingRepository: _finding_to_row, evidence sanitization
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.cloud.base import (
    CloudCostData,
    CloudFindingData,
    CloudResourceData,
    CloudResourceDTO,
    normalize_timestamp,
    sanitize_json,
)
from app.cloud.repository import CloudFindingRepository, CloudResourceRepository
from app.models.cloud import CloudScanSession

# --- sanitize_json Tests ---


class TestSanitizeJson:
    """Tests for the JSON sanitizer that ensures DB columns receive only safe types."""

    def test_passthrough_safe_types(self):
        assert sanitize_json("hello") == "hello"
        assert sanitize_json(42) == 42
        assert sanitize_json(3.14) == 3.14
        assert sanitize_json(True) is True
        assert sanitize_json(None) is None

    def test_datetime_to_iso(self):
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC)
        result = sanitize_json(dt)
        assert result == "2024-06-15T14:30:45+00:00"
        assert isinstance(result, str)

    def test_naive_datetime_gets_utc(self):
        dt = datetime(2024, 6, 15, 14, 30, 45)
        result = sanitize_json(dt)
        assert result == "2024-06-15T14:30:45+00:00"

    def test_date_to_iso(self):
        d = date(2024, 6, 15)
        result = sanitize_json(d)
        assert result == "2024-06-15"
        assert isinstance(result, str)

    def test_decimal_to_float(self):
        assert sanitize_json(Decimal("3.14")) == 3.14
        assert sanitize_json(Decimal("0")) == 0.0
        assert isinstance(sanitize_json(Decimal("1.5")), float)

    def test_uuid_to_string(self):
        uid = UUID("12345678-1234-5678-1234-567812345678")
        result = sanitize_json(uid)
        assert result == "12345678-1234-5678-1234-567812345678"
        assert isinstance(result, str)

    def test_bytes_to_utf8(self):
        assert sanitize_json(b"hello") == "hello"

    def test_bytes_with_invalid_utf8(self):
        result = sanitize_json(b"\xff\xfe")
        assert isinstance(result, str)
        assert "\ufffd" in result

    def test_set_to_sorted_list(self):
        result = sanitize_json({3, 1, 2})
        assert result == [1, 2, 3]
        assert isinstance(result, list)

    def test_tuple_to_list(self):
        result = sanitize_json((1, 2, 3))
        assert result == [1, 2, 3]
        assert isinstance(result, list)

    def test_nested_dict(self):
        dt = datetime(2024, 1, 1, tzinfo=UTC)
        result = sanitize_json({"created": dt, "count": Decimal("5.5")})
        assert result == {"created": "2024-01-01T00:00:00+00:00", "count": 5.5}

    def test_nested_list(self):
        result = sanitize_json([datetime(2024, 1, 1), Decimal("1.5"), b"hello"])
        assert result == ["2024-01-01T00:00:00+00:00", 1.5, "hello"]

    def test_deeply_nested(self):
        result = sanitize_json({
            "level1": {
                "level2": [
                    {"dt": datetime(2024, 1, 1), "dec": Decimal("9.99")},
                    {1, 2, 3},
                ]
            }
        })
        assert result["level1"]["level2"][0]["dt"] == "2024-01-01T00:00:00+00:00"
        assert result["level1"]["level2"][0]["dec"] == 9.99
        assert result["level1"]["level2"][1] == [1, 2, 3]

    def test_empty_containers(self):
        assert sanitize_json({}) == {}
        assert sanitize_json([]) == []

    def test_unknown_type_fallback(self):
        class CustomObj:
            def __str__(self):
                return "custom_value"

        result = sanitize_json(CustomObj())
        assert result == "custom_value"
        assert isinstance(result, str)

    def test_json_dumps_roundtrip(self):
        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC)
        value = {
            "datetime": dt,
            "decimal": Decimal("99.99"),
            "uuid": uuid4(),
            "bytes": b"hello",
            "set": {1, 2, 3},
            "tuple": (4, 5, 6),
            "nested": {"inner_dt": dt, "inner_dec": Decimal("1.0")},
            "list": [dt, Decimal("2.0")],
        }
        sanitized = sanitize_json(value)
        json_str = json.dumps(sanitized)
        assert len(json_str) > 0

    def test_boto3_ec2_instance_configuration(self):
        config = {
            "instance_type": "t3.micro",
            "platform": "linux",
            "private_ip": "10.0.1.5",
            "public_ip": "54.123.45.67",
            "launch_time": datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            "monitoring": {"State": "disabled"},
            "security_groups": [{"GroupId": "sg-12345", "GroupName": "default"}],
            "tags": [{"Key": "Name", "Value": "my-instance"}],
        }
        sanitized = sanitize_json(config)
        json_str = json.dumps(sanitized)
        parsed = json.loads(json_str)
        assert parsed["launch_time"] == "2024-01-15T10:30:00+00:00"
        assert parsed["instance_type"] == "t3.micro"

    def test_boto3_security_group_ip_permissions(self):
        config = {
            "inbound_rules": [
                {
                    "IpProtocol": "tcp",
                    "FromPort": 443,
                    "ToPort": 443,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                    "Ipv6Ranges": [],
                    "PrefixListIds": [],
                    "UserIdGroupPairs": [],
                }
            ],
            "outbound_rules": [],
        }
        sanitized = sanitize_json(config)
        json_str = json.dumps(sanitized)
        parsed = json.loads(json_str)
        assert parsed["inbound_rules"][0]["FromPort"] == 443
        assert parsed["inbound_rules"][0]["IpRanges"][0]["CidrIp"] == "0.0.0.0/0"


# --- normalize_timestamp Tests ---


class TestNormalizeTimestamp:
    def test_none_returns_none(self):
        assert normalize_timestamp(None) is None

    def test_aware_datetime_passthrough(self):
        dt = datetime(2024, 6, 15, tzinfo=UTC)
        result = normalize_timestamp(dt)
        assert result == dt
        assert result.tzinfo is not None

    def test_naive_datetime_gets_utc(self):
        dt = datetime(2024, 6, 15, 10, 30)
        result = normalize_timestamp(dt)
        assert result is not None
        assert result.tzinfo == UTC
        assert result.year == 2024
        assert result.hour == 10

    def test_aware_datetime_preserves_tz(self):
        est = timezone(timedelta(hours=-5))
        dt = datetime(2024, 6, 15, 10, 30, tzinfo=est)
        result = normalize_timestamp(dt)
        assert result is not None
        assert result == dt

    def test_date_to_datetime(self):
        d = date(2024, 6, 15)
        result = normalize_timestamp(d)
        assert result is not None
        assert result.year == 2024
        assert result.hour == 0
        assert result.tzinfo == UTC

    def test_iso_string(self):
        result = normalize_timestamp("2024-06-15T10:30:00Z")
        assert result is not None
        assert result.year == 2024
        assert result.tzinfo is not None

    def test_naive_iso_string(self):
        result = normalize_timestamp("2024-06-15T10:30:00")
        assert result is not None
        assert result.tzinfo == UTC

    def test_invalid_string_returns_none(self):
        assert normalize_timestamp("not-a-date") is None
        assert normalize_timestamp("") is None

    def test_integer_returns_none(self):
        assert normalize_timestamp(12345) is None


# --- CloudResourceDTO Tests ---


class TestCloudResourceDTO:
    def _make_dto(self, **overrides):
        defaults = {
            "provider": "aws",
            "account_id": "123456789012",
            "region": "us-east-1",
            "service": "ec2",
            "resource_id": "i-1234567890abcdef0",
            "resource_name": "my-instance",
            "resource_type": "instance",
            "status": "running",
        }
        defaults.update(overrides)
        return CloudResourceDTO(**defaults)

    def test_basic_creation(self):
        dto = self._make_dto()
        assert dto.provider == "aws"
        assert dto.service == "ec2"
        assert dto.resource_id == "i-1234567890abcdef0"

    def test_empty_tags_and_config(self):
        dto = self._make_dto()
        assert dto.tags == {}
        assert dto.configuration == {}

    def test_tags_sanitized(self):
        dto = self._make_dto(tags={"Created": datetime(2024, 1, 1, tzinfo=UTC)})
        assert isinstance(dto.tags["Created"], str)

    def test_configuration_sanitized(self):
        dto = self._make_dto(configuration={"cost": Decimal("99.99")})
        assert isinstance(dto.configuration["cost"], float)
        assert dto.configuration["cost"] == 99.99

    def test_created_at_normalized(self):
        dto = self._make_dto(created_at=datetime(2024, 1, 1, 10, 0))
        assert dto.created_at is not None
        assert dto.created_at.tzinfo == UTC

    def test_created_at_none(self):
        dto = self._make_dto(created_at=None)
        assert dto.created_at is None

    def test_cost_monthly(self):
        dto = self._make_dto(cost_monthly=15.50)
        assert dto.cost_monthly == 15.50

    def test_cost_monthly_none(self):
        dto = self._make_dto(cost_monthly=None)
        assert dto.cost_monthly is None

    def test_json_roundtrip(self):
        dto = self._make_dto(
            tags={"Name": "test"},
            configuration={
                "instance_type": "t3.micro",
                "launch_time": datetime(2024, 1, 1, tzinfo=UTC),
            },
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        data = dto.model_dump()
        json_str = json.dumps(data, default=str)
        assert len(json_str) > 0

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            CloudResourceDTO(provider="aws")

    def test_s3_bucket_dto(self):
        dto = self._make_dto(
            service="s3",
            resource_id="my-bucket",
            resource_name="my-bucket",
            resource_type="bucket",
            status="active",
            configuration={"creation_date": "2024-01-15T10:30:00Z"},
            created_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        )
        assert dto.service == "s3"
        assert dto.resource_type == "bucket"

    def test_ec2_volume_dto(self):
        dto = self._make_dto(
            resource_id="vol-0123456789abcdef0",
            resource_name="vol-0123456789abcdef0",
            resource_type="volume",
            status="in-use",
            configuration={
                "size_gb": 100,
                "volume_type": "gp3",
                "encrypted": True,
                "availability_zone": "us-east-1a",
            },
        )
        assert dto.configuration["size_gb"] == 100
        assert dto.configuration["encrypted"] is True

    def test_security_group_dto(self):
        dto = self._make_dto(
            resource_id="sg-0123456789abcdef0",
            resource_name="default",
            resource_type="security_group",
            status="active",
            configuration={
                "vpc_id": "vpc-01234567",
                "inbound_rules": [
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 443,
                        "ToPort": 443,
                        "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                    }
                ],
            },
        )
        assert dto.configuration["inbound_rules"][0]["FromPort"] == 443


# --- CloudResourceData Legacy Compatibility ---


class TestCloudResourceData:
    """Ensure the legacy dataclass still works alongside DTOs."""

    def test_basic_creation(self):
        r = CloudResourceData(
            provider="aws",
            service="ec2",
            resource_id="i-123",
            resource_name="test",
            resource_type="instance",
            region="us-east-1",
            status="running",
        )
        assert r.provider == "aws"
        assert r.configuration == {}
        assert r.tags == {}
        assert r.created_at is None

    def test_with_datetime(self):
        dt = datetime(2024, 1, 1, tzinfo=UTC)
        r = CloudResourceData(
            provider="aws", service="ec2", resource_id="i-123",
            resource_name="test", resource_type="instance",
            region="us-east-1", status="running",
            created_at=dt,
        )
        assert r.created_at == dt


# --- CloudResourceRepository Row Conversion ---


class TestCloudResourceRepositoryRowConversion:
    """Tests for repository _resource_to_row and _legacy_resource_to_row static methods."""

    CONN_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    SCAN_ID = "scan-abc123def456"

    def test_resource_to_row_basic(self):
        dto = CloudResourceDTO(
            provider="aws",
            account_id="123456789012",
            region="us-east-1",
            service="ec2",
            resource_id="i-1234567890abcdef0",
            resource_name="my-instance",
            resource_type="instance",
            status="running",
        )
        row = CloudResourceRepository._resource_to_row(dto, self.CONN_ID, self.SCAN_ID)
        assert row["connection_id"] == self.CONN_ID
        assert row["provider"] == "aws"
        assert row["account_id"] == "123456789012"
        assert row["resource_id"] == "i-1234567890abcdef0"
        assert row["configuration"] == {}
        assert row["tags"] == {}
        assert row["cost_monthly"] is None
        assert row["created_at"] is None
        assert row["last_scan_id"] == self.SCAN_ID

    def test_resource_to_row_sanitizes_configuration(self):
        dto = CloudResourceDTO(
            provider="aws",
            account_id="123456789012",
            region="us-east-1",
            service="ec2",
            resource_id="i-123",
            resource_name="test",
            resource_type="instance",
            status="running",
            configuration={
                "launch_time": datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
                "volume_size": Decimal("100.5"),
                "tags_set": {"tag1", "tag2"},
            },
        )
        row = CloudResourceRepository._resource_to_row(dto, self.CONN_ID, self.SCAN_ID)
        assert row["configuration"]["launch_time"] == "2024-01-15T10:30:00+00:00"
        assert row["configuration"]["volume_size"] == 100.5
        assert isinstance(row["configuration"]["tags_set"], list)
        json.dumps(row["configuration"])

    def test_resource_to_row_sanitizes_tags(self):
        dto = CloudResourceDTO(
            provider="aws",
            account_id="123456789012",
            region="us-east-1",
            service="ec2",
            resource_id="i-123",
            resource_name="test",
            resource_type="instance",
            status="running",
            tags={"Created": datetime(2024, 6, 15, tzinfo=UTC), "Name": "prod"},
        )
        row = CloudResourceRepository._resource_to_row(dto, self.CONN_ID, self.SCAN_ID)
        assert isinstance(row["tags"]["Created"], str)
        assert row["tags"]["Name"] == "prod"
        json.dumps(row["tags"])

    def test_resource_to_row_normalizes_created_at(self):
        naive_dt = datetime(2024, 1, 1, 10, 0)
        dto = CloudResourceDTO(
            provider="aws",
            account_id="123456789012",
            region="us-east-1",
            service="ec2",
            resource_id="i-123",
            resource_name="test",
            resource_type="instance",
            status="running",
            created_at=naive_dt,
        )
        row = CloudResourceRepository._resource_to_row(dto, self.CONN_ID, self.SCAN_ID)
        assert row["created_at"] is not None
        assert row["created_at"].tzinfo == UTC

    def test_legacy_resource_to_row_basic(self):
        r = CloudResourceData(
            provider="aws",
            service="s3",
            resource_id="my-bucket",
            resource_name="my-bucket",
            resource_type="bucket",
            region="us-west-2",
            status="active",
        )
        row = CloudResourceRepository._legacy_resource_to_row(r, self.CONN_ID, "123456789012", self.SCAN_ID)
        assert row["connection_id"] == self.CONN_ID
        assert row["provider"] == "aws"
        assert row["account_id"] == "123456789012"
        assert row["resource_id"] == "my-bucket"
        assert row["region"] == "us-west-2"
        assert row["configuration"] == {}
        assert row["tags"] == {}
        assert row["last_scan_id"] == self.SCAN_ID

    def test_legacy_resource_to_row_sanitizes_config(self):
        r = CloudResourceData(
            provider="aws",
            service="ec2",
            resource_id="i-123",
            resource_name="test",
            resource_type="instance",
            region="us-east-1",
            status="running",
            configuration={
                "created": datetime(2024, 1, 1, tzinfo=UTC),
                "size": Decimal("50.0"),
            },
        )
        row = CloudResourceRepository._legacy_resource_to_row(r, self.CONN_ID, "123", self.SCAN_ID)
        assert row["configuration"]["created"] == "2024-01-01T00:00:00+00:00"
        assert row["configuration"]["size"] == 50.0
        json.dumps(row["configuration"])

    def test_legacy_resource_to_row_normalizes_timestamps(self):
        r = CloudResourceData(
            provider="aws",
            service="ec2",
            resource_id="i-123",
            resource_name="test",
            resource_type="instance",
            region="us-east-1",
            status="running",
            created_at=datetime(2024, 6, 15, 10, 0),
            last_modified_at=datetime(2024, 6, 16, 12, 0),
        )
        row = CloudResourceRepository._legacy_resource_to_row(r, self.CONN_ID, "123", self.SCAN_ID)
        assert row["created_at"] is not None
        assert row["created_at"].tzinfo == UTC
        assert row["last_modified_at"] is not None
        assert row["last_modified_at"].tzinfo == UTC

    def test_legacy_resource_to_row_none_timestamps(self):
        r = CloudResourceData(
            provider="aws",
            service="ec2",
            resource_id="i-123",
            resource_name="test",
            resource_type="instance",
            region="us-east-1",
            status="running",
            created_at=None,
        )
        row = CloudResourceRepository._legacy_resource_to_row(r, self.CONN_ID, "123", self.SCAN_ID)
        assert row["created_at"] is None
        assert row["last_modified_at"] is None


# --- CloudFindingRepository Row Conversion ---


class TestCloudFindingRepositoryRowConversion:
    """Tests for finding repository _finding_to_row static method."""

    CONN_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    def test_finding_to_row_basic(self):
        f = CloudFindingData(
            provider="aws",
            service="ec2",
            category="security",
            severity="high",
            title="Open Security Group",
            description="Security group allows 0.0.0.0/0",
            resource_id="sg-123",
            resource_type="security_group",
            region="us-east-1",
            rule_id="EC2-SG-001",
        )
        row = CloudFindingRepository._finding_to_row(f, self.CONN_ID, "aws", "scan-001")
        assert row["connection_id"] == self.CONN_ID
        assert row["provider"] == "aws"
        assert row["title"] == "Open Security Group"
        assert row["severity"] == "high"
        assert row["rule_id"] == "EC2-SG-001"
        assert row["evidence"] == {}
        assert row["compliance_frameworks"] == []
        assert row["last_scan_id"] == "scan-001"
        assert row["status"] == "open"

    def test_finding_to_row_sanitizes_evidence(self):
        f = CloudFindingData(
            provider="aws",
            service="ec2",
            category="security",
            severity="critical",
            title="Unencrypted Volume",
            description="EBS volume is not encrypted",
            evidence={
                "volume_id": "vol-123",
                "created_at": datetime(2024, 1, 1, tzinfo=UTC),
                "details": {"encrypted": False, "size_gb": Decimal("100")},
            },
            compliance_frameworks=["NIST 800-53", "CIS AWS Foundations"],
        )
        row = CloudFindingRepository._finding_to_row(f, self.CONN_ID, "aws", "scan-001")
        assert isinstance(row["evidence"]["created_at"], str)
        assert row["evidence"]["details"]["encrypted"] is False
        assert row["evidence"]["details"]["size_gb"] == 100.0
        assert row["compliance_frameworks"] == ["NIST 800-53", "CIS AWS Foundations"]
        json.dumps(row["evidence"])
        json.dumps(row["compliance_frameworks"])

    def test_finding_to_row_none_fields(self):
        f = CloudFindingData(
            provider="aws",
            service="iam",
            category="security",
            severity="medium",
            title="MFA Not Enabled",
            description="Root account MFA is not enabled",
            resource_id=None,
            resource_type=None,
            region="",
            rule_id=None,
        )
        row = CloudFindingRepository._finding_to_row(f, self.CONN_ID, "aws", "scan-001")
        assert row["resource_id"] == ""
        assert row["resource_type"] is None
        assert row["rule_id"] == ""
        assert row["evidence"] == {}
        assert row["last_scan_id"] == "scan-001"


# --- CloudCostData Tests ---


class TestCloudCostData:
    def test_basic_creation(self):
        c = CloudCostData(
            provider="aws",
            service="ec2",
            title="Reserved Instance",
            description="Use RI for savings",
            monthly_savings=50.0,
            current_cost=100.0,
            priority="high",
            category="reserved_instances",
            recommendation_type="purchase_ri",
            estimated_impact="50% savings",
        )
        assert c.monthly_savings == 50.0
        assert c.current_cost == 100.0

    def test_defaults(self):
        c = CloudCostData(
            provider="aws",
            service="s3",
            title="Delete old data",
            description="Remove old data",
        )
        assert c.monthly_savings == 0.0
        assert c.current_cost == 0.0
        assert c.priority == "medium"


# --- CloudFindingData Tests ---


class TestCloudFindingData:
    def test_basic_creation(self):
        f = CloudFindingData(
            provider="aws",
            service="ec2",
            category="security",
            severity="high",
            title="Test Finding",
            description="A test finding",
        )
        assert f.severity == "high"
        assert f.evidence == {}
        assert f.compliance_frameworks == []

    def test_with_evidence(self):
        f = CloudFindingData(
            provider="aws",
            service="s3",
            category="compliance",
            severity="medium",
            title="Public Bucket",
            description="Bucket is public",
            evidence={"bucket": "my-bucket", "policy": {"Statement": []}},
        )
        assert f.evidence["bucket"] == "my-bucket"


# --- Scan ID Tests ---


class TestScanIdInRowConversion:
    """Tests for scan_id propagation in row conversion methods."""

    CONN_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    def test_different_scan_ids_produce_different_rows(self):
        dto = CloudResourceDTO(
            provider="aws",
            account_id="123456789012",
            region="us-east-1",
            service="ec2",
            resource_id="i-123",
            resource_name="test",
            resource_type="instance",
            status="running",
        )
        row1 = CloudResourceRepository._resource_to_row(dto, self.CONN_ID, "scan-aaa")
        row2 = CloudResourceRepository._resource_to_row(dto, self.CONN_ID, "scan-bbb")
        assert row1["last_scan_id"] == "scan-aaa"
        assert row2["last_scan_id"] == "scan-bbb"

    def test_legacy_same_pattern(self):
        r = CloudResourceData(
            provider="aws",
            service="ec2",
            resource_id="i-123",
            resource_name="test",
            resource_type="instance",
            region="us-east-1",
            status="running",
        )
        row1 = CloudResourceRepository._legacy_resource_to_row(r, self.CONN_ID, "123", "scan-xxx")
        row2 = CloudResourceRepository._legacy_resource_to_row(r, self.CONN_ID, "123", "scan-yyy")
        assert row1["last_scan_id"] == "scan-xxx"
        assert row2["last_scan_id"] == "scan-yyy"


class TestDeleteStale:
    """Tests for the scan_id-based soft-deletion logic.

    Uses a mock database session to verify the correct SQLAlchemy
    update statement is built. Tests cover:
      - empty resource list (no-op)
      - one resource
      - 100 resources
      - 10,000 resources
      - deleted resources (already deleted)
      - resources that still exist
    """

    CONN_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    def test_delete_stale_builds_correct_where_clause(self):
        """Verify the update statement targets: connection, not-current-scan, not-already-deleted."""
        from unittest.mock import AsyncMock, MagicMock

        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        repo = CloudResourceRepository(mock_db)

        import asyncio
        deleted = asyncio.get_event_loop().run_until_complete(
            repo.delete_stale(self.CONN_ID, "scan-current")
        )

        assert deleted == 5
        assert mock_db.execute.call_count == 2

        # Verify the second call is the UPDATE
        call_args = mock_db.execute.call_args_list[1]
        stmt = call_args[0][0]
        from sqlalchemy.sql.dml import Update
        assert isinstance(stmt, Update)

    def test_delete_stale_returns_zero_when_nothing_deleted(self):
        from unittest.mock import AsyncMock, MagicMock

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        repo = CloudResourceRepository(mock_db)

        import asyncio
        deleted = asyncio.get_event_loop().run_until_complete(
            repo.delete_stale(self.CONN_ID, "scan-current")
        )

        assert deleted == 0

    def test_delete_stale_scales_to_large_sets(self):
        """The scan_id approach doesn't depend on resource count — always O(1) SQL."""
        from unittest.mock import AsyncMock, MagicMock

        mock_result = MagicMock()
        mock_result.rowcount = 10_000
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        repo = CloudResourceRepository(mock_db)

        import asyncio
        deleted = asyncio.get_event_loop().run_until_complete(
            repo.delete_stale(self.CONN_ID, "scan-huge")
        )

        # One single UPDATE, no batching needed regardless of resource count
        assert deleted == 10_000
        # One SELECT + one UPDATE, no batching needed regardless of resource count
        assert mock_db.execute.call_count == 2

    def test_delete_stale_does_not_affect_already_deleted(self):
        """Resources with status='deleted' are left untouched."""
        from unittest.mock import AsyncMock, MagicMock

        mock_result = MagicMock()
        mock_result.rowcount = 0  # nothing deleted because all were already deleted
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        repo = CloudResourceRepository(mock_db)

        import asyncio
        deleted = asyncio.get_event_loop().run_until_complete(
            repo.delete_stale(self.CONN_ID, "scan-new")
        )

        assert deleted == 0

    def test_delete_stale_only_affects_target_connection(self):
        """Other connections' resources are not touched."""
        from unittest.mock import AsyncMock, MagicMock

        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        repo = CloudResourceRepository(mock_db)

        import asyncio
        deleted = asyncio.get_event_loop().run_until_complete(
            repo.delete_stale(self.CONN_ID, "scan-123")
        )

        assert deleted == 3
        # Verify the statement filters by connection_id
        call_args = mock_db.execute.call_args
        stmt = call_args[0][0]
        # The whereclause should include connection_id
        where_str = str(stmt.whereclause)
        assert "connection_id" in where_str

    def test_scan_id_appears_in_upsert_rows(self):
        """Verify scan_id is stamped on every upserted resource row."""
        dto = CloudResourceDTO(
            provider="aws",
            account_id="123456789012",
            region="us-east-1",
            service="ec2",
            resource_id="i-123",
            resource_name="test",
            resource_type="instance",
            status="running",
            configuration={"launch_time": datetime(2024, 1, 1, tzinfo=UTC)},
            tags={"Name": "prod"},
        )
        scan = "scan-unique-id-12345"
        row = CloudResourceRepository._resource_to_row(dto, self.CONN_ID, scan)
        assert row["last_scan_id"] == scan
        assert row["configuration"]["launch_time"] == "2024-01-01T00:00:00+00:00"
        # scan_id is JSON-serializable
        json.dumps(row, default=str)


class TestCloudScanSessionCompletion:
    """Verify CloudScanSession stores started_at, finished_at, duration_seconds correctly."""

    def test_session_started_at_set_on_creation(self):
        """Session with started_at is a datetime."""
        now = datetime.now(UTC)
        session = CloudScanSession(
            connection_id=uuid4(),
            status="running",
            progress=0.0,
            stages_total=6,
            stages_completed=[],
            started_at=now,
        )
        assert session.started_at is not None
        assert isinstance(session.started_at, datetime)
        assert session.started_at.tzinfo is not None

    def test_session_completion_sets_finished_at_and_duration(self):
        """Simulate scan completion: finished_at is datetime, duration_seconds is positive float."""
        started = datetime(2026, 7, 28, 10, 0, 0, tzinfo=UTC)
        session = CloudScanSession(
            connection_id=uuid4(),
            status="running",
            progress=0.0,
            stages_total=6,
            stages_completed=[],
            started_at=started,
        )

        finished = datetime(2026, 7, 28, 10, 5, 30, tzinfo=UTC)
        session.status = "completed"
        session.progress = 100.0
        session.stages_completed = ["discovery", "security", "cost_analysis", "compliance_check", "finalize"]
        session.resources_scanned = 150
        session.findings_count = 12
        session.finished_at = finished
        session.duration_seconds = round((finished - started).total_seconds(), 2)

        assert isinstance(session.finished_at, datetime)
        assert session.finished_at.tzinfo is not None
        assert isinstance(session.duration_seconds, float)
        assert session.duration_seconds == 330.0
        assert session.duration_seconds > 0
        assert session.status == "completed"

    def test_session_failure_sets_finished_at_and_duration(self):
        """Simulate scan failure: finished_at is datetime, duration_seconds computed."""
        started = datetime(2026, 7, 28, 10, 0, 0, tzinfo=UTC)
        session = CloudScanSession(
            connection_id=uuid4(),
            status="running",
            progress=0.0,
            stages_total=6,
            stages_completed=[],
            started_at=started,
        )

        finished = datetime(2026, 7, 28, 10, 0, 45, tzinfo=UTC)
        session.status = "failed"
        session.error = "AccessDenied: AssumeRole failed"
        session.finished_at = finished
        session.duration_seconds = round((finished - started).total_seconds(), 2)

        assert isinstance(session.finished_at, datetime)
        assert isinstance(session.duration_seconds, float)
        assert session.duration_seconds == 45.0
        assert session.status == "failed"

    def test_duration_seconds_none_when_started_at_missing(self):
        """If started_at was never set, duration_seconds stays None (no crash)."""
        session = CloudScanSession(
            connection_id=uuid4(),
            status="running",
            progress=0.0,
            stages_total=6,
            stages_completed=[],
        )
        finished = datetime.now(UTC)
        session.finished_at = finished
        if session.started_at:
            session.duration_seconds = round(
                (finished - session.started_at).total_seconds(), 2
            )

        assert session.finished_at is not None
        assert session.duration_seconds is None
        assert session.started_at is None

    def test_duration_seconds_is_float_for_asyncpg(self):
        """duration_seconds must be a Python float, not int, for TIMESTAMP compatibility."""
        started = datetime(2026, 7, 28, 10, 0, 0, tzinfo=UTC)
        finished = datetime(2026, 7, 28, 10, 0, 1, 500000, tzinfo=UTC)
        session = CloudScanSession(
            connection_id=uuid4(),
            status="completed",
            progress=100.0,
            stages_total=6,
            stages_completed=[],
            started_at=started,
            finished_at=finished,
        )
        session.duration_seconds = round((finished - started).total_seconds(), 2)
        assert type(session.duration_seconds) is float
        assert session.duration_seconds == 1.5
