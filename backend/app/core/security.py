"""Security module for authentication and authorization."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.models.user import User

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
    prefix = f"dk_{secrets.token_urlsafe(4)}"
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
    expire = datetime.now(UTC) + timedelta(days=7)
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
) -> User | None:
    """Get current user from JWT token."""
    payload = decode_token(token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    # User.id is a UUID, not an integer
    try:
        user_uuid = UUID(user_id)
    except (ValueError, AttributeError):
        return None

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if user and not user.is_active:
        return None

    return user


async def get_current_user_from_api_key(
    api_key: str,
    db: AsyncSession,
) -> User | None:
    """Get current user from API key."""
    # Extract prefix for faster lookup
    if "_" not in api_key:
        return None

    prefix = api_key.split("_")[0]
    if not prefix.startswith("dk_"):
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
) -> User:
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
) -> User | None:
    """Get current user if authenticated, None otherwise."""
    try:
        return await get_current_user(request, credentials, api_key, db)
    except HTTPException:
        return None


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require user to have admin role."""
    if current_user.role.value not in ["admin", "enterprise"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_enterprise(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require user to have enterprise role."""
    if current_user.role.value != "enterprise":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enterprise access required",
        )
    return current_user
