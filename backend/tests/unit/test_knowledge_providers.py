"""Integration tests for AWS Knowledge Providers.

Tests for AWS providers with mocked boto3 sessions to verify
the complete retrieval flow without actual AWS API calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import UTC, datetime

from app.knowledge.base import KnowledgeDocument


class TestAWSServiceQuotasProvider:
    """Tests for AWS Service Quotas provider with mocked boto3."""

    @pytest.fixture
    def mock_boto_session(self):
        """Create a mocked boto3 session."""
        session = MagicMock()
        client = MagicMock()
        session.client.return_value = client
        return session, client

    @pytest.mark.asyncio
    async def test_retrieve_service_limits(self, mock_boto_session):
        """Test retrieving service limits."""
        session, client = mock_boto_session

        # Mock the service quotas API response
        client.list_services.return_value = {
            "Services": [
                {"ServiceCode": "ec2", "ServiceName": "Amazon EC2"},
            ]
        }

        client.list_service_quotas.return_value = {
            "Quotas": [
                {
                    "ServiceCode": "ec2",
                    "ServiceName": "Amazon EC2",
                    "QuotaArn": "arn:aws:servicequotas:us-east-1::quota/ec2/L-0263D0A6",
                    "QuotaCode": "L-0263D0A6",
                    "QuotaName": "Running On-Demand Standard instances",
                    "Value": 1920.0,
                    "Unit": "None",
                }
            ]
        }

        from app.knowledge.aws_service_quotas import AWSServiceQuotasProvider

        provider = AWSServiceQuotasProvider(boto_session=session)
        docs = await provider.retrieve("EC2 instance limits", service="ec2")

        assert len(docs) > 0
        assert any("ec2" in doc.title.lower() or "ec2" in doc.metadata.get("service", "").lower() for doc in docs)

    @pytest.mark.asyncio
    async def test_retrieve_returns_fallback_on_error(self, mock_boto_session):
        """Test that fallback data is returned when API fails."""
        session, client = mock_boto_session
        client.list_services.side_effect = Exception("API Error")

        from app.knowledge.aws_service_quotas import AWSServiceQuotasProvider

        provider = AWSServiceQuotasProvider(boto_session=session)
        docs = await provider.retrieve("EC2 limits", service="ec2")

        # Should return fallback data
        assert len(docs) > 0


class TestAWSTrustedAdvisorProvider:
    """Tests for AWS Trusted Advisor provider with mocked boto3."""

    @pytest.fixture
    def mock_boto_session(self):
        """Create a mocked boto3 session."""
        session = MagicMock()
        client = MagicMock()
        session.client.return_value = client
        return session, client

    @pytest.mark.asyncio
    async def test_retrieve_trusted_advisor_checks(self, mock_boto_session):
        """Test retrieving Trusted Advisor checks."""
        session, client = mock_boto_session

        # Mock the support API response
        client.describe_trusted_advisor_checks.return_value = {
            "checks": [
                {
                    "id": "abc123",
                    "name": "Security Groups - Specific Ports Unrestricted",
                    "category": "security",
                    "description": "Checks security groups for unrestricted access",
                }
            ]
        }

        client.describe_trusted_advisor_check_result.return_value = {
            "result": {
                "status": "warning",
                "flaggedResources": [
                    {
                        "status": "warning",
                        "resourceId": "sg-12345",
                        "metadata": ["us-east-1", "sg-12345", "0.0.0.0/0"],
                    }
                ],
            }
        }

        from app.knowledge.aws_trusted_advisor import AWSTrustedAdvisorProvider

        provider = AWSTrustedAdvisorProvider(boto_session=session)
        docs = await provider.retrieve("security group unrestricted access")

        assert len(docs) > 0
        assert any("security" in doc.title.lower() or "trusted" in doc.title.lower() for doc in docs)

    @pytest.mark.asyncio
    async def test_retrieve_returns_fallback_on_error(self, mock_boto_session):
        """Test that fallback data is returned when API fails."""
        session, client = mock_boto_session
        client.describe_trusted_advisor_checks.side_effect = Exception("Access Denied")

        from app.knowledge.aws_trusted_advisor import AWSTrustedAdvisorProvider

        provider = AWSTrustedAdvisorProvider(boto_session=session)
        docs = await provider.retrieve("security best practices")

        # Should return fallback data
        assert len(docs) > 0


class TestAWSCostExplorerProvider:
    """Tests for AWS Cost Explorer provider with mocked boto3."""

    @pytest.fixture
    def mock_boto_session(self):
        """Create a mocked boto3 session."""
        session = MagicMock()
        client = MagicMock()
        session.client.return_value = client
        return session, client

    @pytest.mark.asyncio
    async def test_retrieve_cost_data(self, mock_boto_session):
        """Test retrieving cost data."""
        session, client = mock_boto_session

        # Mock the cost explorer API response
        client.get_cost_and_usage.return_value = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01", "End": "2024-01-31"},
                    "Groups": [
                        {
                            "Keys": ["Amazon EC2"],
                            "Metrics": {
                                "UnblendedCost": {"Amount": "1500.00", "Unit": "USD"},
                            },
                        }
                    ],
                }
            ],
            "DimensionValuesAttributes": [],
        }

        client.get_cost_recommendations.return_value = {
            "CostRecommendations": [
                {
                    "AccountId": "123456789012",
                    "FindingDescription": "EC2 instance underutilized",
                    "RecommendationId": "rec-123",
                    "RecommendationSummary": "Consider downsizing EC2 instances",
                    "ResourceDetails": {"ec2InstanceId": "i-12345"},
                    "SavingsAmount": {"Amount": "100.00", "Unit": "USD"},
                }
            ]
        }

        from app.knowledge.aws_cost_explorer import AWSCostExplorerProvider

        provider = AWSCostExplorerProvider(boto_session=session)
        docs = await provider.retrieve("EC2 cost optimization")

        assert len(docs) > 0
        assert any("cost" in doc.title.lower() or "ec2" in doc.title.lower() for doc in docs)

    @pytest.mark.asyncio
    async def test_retrieve_returns_fallback_on_error(self, mock_boto_session):
        """Test that fallback data is returned when API fails."""
        session, client = mock_boto_session
        client.get_cost_and_usage.side_effect = Exception("Access Denied")

        from app.knowledge.aws_cost_explorer import AWSCostExplorerProvider

        provider = AWSCostExplorerProvider(boto_session=session)
        docs = await provider.retrieve("cost optimization")

        # Should return fallback data
        assert len(docs) > 0


class TestSearchClient:
    """Tests for search client functionality."""

    def test_fallback_search_client(self):
        """Test fallback search client."""
        from app.knowledge.search import FallbackSearchClient

        client = FallbackSearchClient()
        results = client.search("test query")
        assert results == []
        assert client.health_check() is True

    def test_get_search_client_returns_fallback(self):
        """Test that get_search_client returns fallback when no API configured."""
        from app.knowledge.search import get_search_client, FallbackSearchClient

        client = get_search_client()
        assert isinstance(client, FallbackSearchClient)


class TestKnowledgeRegistryIntegration:
    """Integration tests for KnowledgeRegistry with mocked providers."""

    @pytest.mark.asyncio
    async def test_registry_retrieve_with_metrics(self):
        """Test registry retrieve collects metrics."""
        from app.knowledge.registry import KnowledgeRegistry
        from app.knowledge.metrics import get_knowledge_metrics

        registry = KnowledgeRegistry()
        metrics = get_knowledge_metrics()
        initial_count = metrics.total_retrievals

        class MockProvider:
            @property
            def name(self):
                return "mock_provider"

            @property
            def description(self):
                return "Mock provider for testing"

            async def retrieve(self, query, *, service="", region="", max_results=5):
                return [
                    KnowledgeDocument(
                        source="mock_provider",
                        title="Mock Document",
                        content="Mock content",
                        url="https://example.com",
                        version="latest",
                    )
                ]

        registry.register(MockProvider())
        docs = await registry.retrieve("test query", max_results=5)

        assert len(docs) == 1
        assert metrics.total_retrievals > initial_count

    @pytest.mark.asyncio
    async def test_registry_health_check(self):
        """Test registry health check."""
        from app.knowledge.registry import KnowledgeRegistry

        registry = KnowledgeRegistry()

        class HealthyProvider:
            @property
            def name(self):
                return "healthy"

            @property
            def description(self):
                return "Healthy provider"

            async def health_check(self):
                return True

        class UnhealthyProvider:
            @property
            def name(self):
                return "unhealthy"

            @property
            def description(self):
                return "Unhealthy provider"

            async def health_check(self):
                return False

        registry.register(HealthyProvider())
        registry.register(UnhealthyProvider())

        health = await registry.health_check()
        assert health["healthy"] is True
        assert health["unhealthy"] is False
