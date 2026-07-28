"""Knowledge provider registration and initialization.

This module handles registering all knowledge providers at application startup.
It ensures the knowledge registry is properly configured with all available
providers before the recommendation engine starts processing requests.
"""

from __future__ import annotations

import logging
from typing import Any

from app.knowledge.registry import KnowledgeRegistry, get_knowledge_registry

logger = logging.getLogger(__name__)


def register_providers(
    registry: KnowledgeRegistry | None = None,
    boto_session: Any | None = None,
    config: Any | None = None,
) -> KnowledgeRegistry:
    """Register all knowledge providers with the registry.

    Args:
        registry: Optional existing registry to use. Creates new if None.
        boto_session: Optional boto3 session for AWS API calls.
        config: Optional settings object for configuration.

    Returns:
        Configured KnowledgeRegistry with all providers registered.
    """
    from app.config import settings

    if registry is None:
        registry = get_knowledge_registry()

    if config is None:
        config = settings

    # Get enabled providers from config
    enabled_providers = getattr(
        config, "KNOWLEDGE_ENABLED_PROVIDERS", "aws_docs,aws_pricing,aws_security,internal_rules"
    )
    if isinstance(enabled_providers, str):
        enabled_set = {p.strip() for p in enabled_providers.split(",")}
    else:
        enabled_set = set(enabled_providers)

    logger.info(
        "KNOWLEDGE_PROVIDER_REGISTRATION_START",
        enabled_providers=sorted(enabled_set),
    )

    # 1. Register AWS Documentation provider
    if "aws_docs" in enabled_set:
        try:
            from app.knowledge.aws_docs import AWSDocsProvider

            provider = AWSDocsProvider(
                use_live_retrieval=getattr(config, "KNOWLEDGE_LIVE_DOCS_ENABLED", False)
            )
            registry.register(provider)
        except Exception as exc:
            logger.error("PROVIDER_REGISTRATION_FAILED", provider="aws_docs", error=str(exc))

    # 2. Register AWS Pricing provider
    if "aws_pricing" in enabled_set:
        try:
            from app.knowledge.aws_pricing import AWSPricingProvider

            provider = AWSPricingProvider(boto_session=boto_session)
            registry.register(provider)
        except Exception as exc:
            logger.error("PROVIDER_REGISTRATION_FAILED", provider="aws_pricing", error=str(exc))

    # 3. Register AWS Security provider
    if "aws_security" in enabled_set:
        try:
            from app.knowledge.aws_security import AWSSecurityProvider

            provider = AWSSecurityProvider()
            registry.register(provider)
        except Exception as exc:
            logger.error("PROVIDER_REGISTRATION_FAILED", provider="aws_security", error=str(exc))

    # 4. Register Internal Rules provider
    if "internal_rules" in enabled_set:
        try:
            from app.knowledge.internal_rules import InternalRulesProvider

            provider = InternalRulesProvider()
            registry.register(provider)
        except Exception as exc:
            logger.error("PROVIDER_REGISTRATION_FAILED", provider="internal_rules", error=str(exc))

    # 5. Register AWS Service Quotas provider
    if "aws_service_quotas" in enabled_set:
        try:
            from app.knowledge.aws_service_quotas import AWSServiceQuotasProvider

            provider = AWSServiceQuotasProvider(boto_session=boto_session)
            registry.register(provider)
        except Exception as exc:
            logger.error(
                "PROVIDER_REGISTRATION_FAILED provider=aws_service_quotas "
                f"error={exc}"
            )

    # 6. Register AWS Trusted Advisor provider
    if "aws_trusted_advisor" in enabled_set:
        try:
            from app.knowledge.aws_trusted_advisor import AWSTrustedAdvisorProvider

            provider = AWSTrustedAdvisorProvider(boto_session=boto_session)
            registry.register(provider)
        except Exception as exc:
            logger.error(
                "PROVIDER_REGISTRATION_FAILED provider=aws_trusted_advisor "
                f"error={exc}"
            )

    # 7. Register AWS Cost Explorer provider
    if "aws_cost_explorer" in enabled_set:
        try:
            from app.knowledge.aws_cost_explorer import AWSCostExplorerProvider

            provider = AWSCostExplorerProvider(boto_session=boto_session)
            registry.register(provider)
        except Exception as exc:
            logger.error(
                "PROVIDER_REGISTRATION_FAILED provider=aws_cost_explorer "
                f"error={exc}"
            )

    logger.info(
        "KNOWLEDGE_PROVIDER_REGISTRATION_COMPLETE",
        registered_providers=sorted(registry.providers.keys()),
        total_providers=len(registry.providers),
    )

    return registry


async def initialize_knowledge_system(
    boto_session: Any | None = None,
    config: Any | None = None,
) -> KnowledgeRegistry:
    """Initialize the complete knowledge system at application startup.

    This should be called during the FastAPI lifespan startup event.
    It registers all providers and performs initial health checks.

    Args:
        boto_session: Optional boto3 session for AWS API calls.
        config: Optional settings object for configuration.

    Returns:
        Configured and initialized KnowledgeRegistry.
    """
    from app.config import settings

    if config is None:
        config = settings

    logger.info("KNOWLEDGE_SYSTEM_INITIALIZATION_START")

    # Register all providers
    registry = register_providers(
        boto_session=boto_session,
        config=config,
    )

    # Perform health checks
    try:
        health = await registry.health_check()
        healthy = [name for name, ok in health.items() if ok]
        unhealthy = [name for name, ok in health.items() if not ok]

        logger.info(
            "KNOWLEDGE_PROVIDER_HEALTH_CHECK",
            healthy_providers=healthy,
            unhealthy_providers=unhealthy,
        )
    except Exception as exc:
        logger.warning("KNOWLEDGE_HEALTH_CHECK_FAILED", error=str(exc))

    # Log cache stats
    try:
        stats = await registry.cache_stats()
        logger.info("KNOWLEDGE_CACHE_STATS", **stats)
    except Exception as exc:
        logger.warning("KNOWLEDGE_CACHE_STATS_FAILED", error=str(exc))

    logger.info(
        "KNOWLEDGE_SYSTEM_INITIALIZATION_COMPLETE",
        total_providers=len(registry.providers),
    )

    return registry
