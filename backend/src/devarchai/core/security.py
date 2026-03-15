"""Security utilities for authentication and authorization."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from devarchai.config import settings
from devarchai.db.session import get_db

logger = structlog.get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
http_bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key with prefix."""
    prefix = f"{settings.API_KEY_PREFIX}_{secrets.token_urlsafe(4)}"
    full_key = f"{prefix}_{secrets.token_urlsafe(32)}"
    return full_key, prefix


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return encoded_jwt


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        return payload
    except JWTError:
        return None


async def get_current_user_from_token(
    token: str,
    db: AsyncSession,
) -> Any | None:
    """Get current user from JWT token."""
    from devarchai.models.user import User

    payload = decode_token(token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user and not user.is_active:
        return None

    return user


async def get_current_user_from_api_key(
    api_key: str,
    db: AsyncSession,
) -> Any | None:
    """Get current user from API key."""
    from devarchai.models.user import User

    # Extract prefix for faster lookup
    if "_" not in api_key:
        return None

    prefix = api_key.split("_")[0]
    if not prefix.startswith(settings.API_KEY_PREFIX + "_"):
        return None

    result = await db.execute(
        select(User).where(
            User.api_key_prefix == prefix,
            User.is_active.is_(True),
        )
    )
    user = result.scalar_one_or_none()

    if user and user.api_key == api_key:
        # Update last login
        user.last_login_at = datetime.now(UTC)
        return user

    return None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    api_key: str | None = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get current authenticated user.

    Supports both JWT tokens (Authorization: Bearer <token>)
    and API keys (X-API-Key: <key>).
    """

    # Try API key first (for enterprise users)
    if api_key:
        user = await get_current_user_from_api_key(api_key, db)
        if user:
            request.state.auth_method = "api_key"
            return user

    # Try JWT token
    if credentials and credentials.credentials:
        user = await get_current_user_from_token(credentials.credentials, db)
        if user:
            request.state.auth_method = "jwt"
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    api_key: str | None = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> Any | None:
    """Get current user if authenticated, None otherwise."""
    try:
        return await get_current_user(request, credentials, api_key, db)
    except HTTPException:
        return None


async def require_admin(
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Require user to have admin role."""
    if current_user.role.value not in ["admin", "enterprise"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_enterprise(
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Require user to have enterprise role."""
    if current_user.role.value != "enterprise":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enterprise access required",
        )
    return current_user


async def get_current_organization(
    request: Request,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any | None:
    """Get current organization from request context."""
    from devarchai.models.organization import Organization

    org_id = request.headers.get("X-Organization-ID")
    if not org_id:
        # Fall back to user's current org
        org_id = current_user.current_org_id

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization ID required",
        )

    # Verify user is member of this organization
    from devarchai.models.user import OrganizationMember

    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization",
        )

    return await db.get(Organization, org_id)
