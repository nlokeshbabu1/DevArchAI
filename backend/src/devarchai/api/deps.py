"""FastAPI dependencies for API endpoints."""

from collections.abc import AsyncGenerator
from typing import Optional

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from devarchai.core.security import (
    get_current_user as get_authenticated_user,
)
from devarchai.db.session import get_session_factory

logger = structlog.get_logger(__name__)

# Security schemes
http_bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session.

    Yields:
        AsyncSession: Database session
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    api_key: Optional[str] = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current authenticated user.

    Supports both JWT tokens and API keys.
    """
    return await get_authenticated_user(request, credentials, api_key, db)


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    api_key: Optional[str] = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user if authenticated, None otherwise.

    Useful for endpoints that work for both authenticated and anonymous users.
    """
    try:
        return await get_current_user(request, credentials, api_key, db)
    except HTTPException:
        return None


async def get_organization_id(request: Request) -> Optional[str]:
    """
    Get organization ID from request headers.

    Used for multi-tenancy support.
    """
    return request.headers.get("X-Organization-ID")


async def require_organization(
    org_id: Optional[str] = Depends(get_organization_id),
) -> str:
    """
    Require organization ID to be present.

    Raises 400 if organization ID is not provided.
    """
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID required. Use X-Organization-ID header.",
        )
    return org_id
