"""Security module for authentication and authorization."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.encryption import decrypt_email, encrypt_email
from app.db.session import get_db
from app.models.user import User

logger = structlog.get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
http_bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_email(email: str) -> str:
    """Create a SHA256 hash of email for database lookups."""
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


def encrypt_user_email(email: str) -> tuple[str, str]:
    """Encrypt email and create hash for storage."""
    encrypted = encrypt_email(email)
    email_hash = hash_email(email)
    return encrypted, email_hash


def decrypt_user_email(encrypted_email: str) -> str:
    """Decrypt an encrypted email."""
    return decrypt_email(encrypted_email)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key with prefix."""
    # Prefix must fit within api_key_prefix String(8): "dk_" + up to 5 chars.
    # token_urlsafe(3) yields exactly 4 base64url chars (3 bytes), giving
    # "dk_xxxx" (7 chars) and never exceeding the varchar(8) column.
    prefix = f"dk_{secrets.token_urlsafe(3)}"
    full_key = f"{prefix}_{secrets.token_urlsafe(32)}"
    return full_key, prefix


def _generate_jti() -> str:
    """Generate a unique JWT ID for token tracking."""
    return str(uuid4())


def hash_token(token: str) -> str:
    """Create a SHA-256 hash of a token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def is_stored_api_key_hash(value: str) -> bool:
    """True when ``value`` looks like a SHA-256 hex digest stored for an API key."""
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


def verify_user_api_key(stored: str | None, presented: str) -> bool:
    """Constant-time verification for legacy plaintext or hashed ``dk_`` API keys."""
    if not stored:
        return False
    if is_stored_api_key_hash(stored):
        return secrets.compare_digest(stored, hash_token(presented))
    return secrets.compare_digest(stored, presented)


JWT_ISSUER = "devarchai"
JWT_AUDIENCE = "devarchai-api"


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token with jti, iat, iss, and aud."""
    to_encode = data.copy()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access",
        "jti": _generate_jti(),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return encoded_jwt


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a JWT refresh token with jti, iat, iss, and aud."""
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "refresh",
        "jti": _generate_jti(),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return encoded_jwt


def decode_token(token: str | None) -> dict[str, Any] | None:
    """Decode and validate a JWT token."""
    if token is None:
        return None
    try:
        # Verify algorithm to prevent algorithm confusion attacks
        unverified_header = jwt.get_unverified_header(token)
        if unverified_header.get("alg") != "HS256":
            logger.warning("JWT algorithm mismatch", alg=unverified_header.get("alg"))
            return None
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={"require": ["exp", "iat", "jti", "sub", "iss", "aud"]},
        )
        if payload.get("jti") is None:
            logger.warning("Missing JWT JTI", payload_keys=list(payload.keys()))
        return payload
    except JWTError:
        return None


def decode_access_token_allow_expired(token: str | None) -> dict[str, Any] | None:
    """Decode access JWT for logout/blacklist when exp may have passed."""
    if token is None:
        return None
    try:
        unverified_header = jwt.get_unverified_header(token)
        if unverified_header.get("alg") != "HS256":
            return None
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options={
                "verify_exp": False,
                "require": ["jti", "sub", "iss", "aud"],
            },
        )
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


async def get_current_user_from_token(
    token: str,
    db: AsyncSession,
    request: Request | None = None,
) -> User | None:
    """Get current user from JWT token with blacklist check."""
    payload = decode_token(token)
    if payload is None:
        return None

    if payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    # Check blacklist — fail closed if Redis is unavailable
    jti = payload.get("jti")
    if jti:
        from app.services.token_blacklist import BlacklistRedisError, is_blacklisted
        try:
            if await is_blacklisted(jti):
                logger.warning("token_blacklisted", jti=jti[:8])
                return None
        except BlacklistRedisError:
            # Fail closed: reject the request if we cannot verify blacklist status
            logger.error("auth_revocation_check_failed", jti=jti[:8], reason="redis_unavailable")
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
    """Get current user from API key.

    Supports both the Settings-page ``sk-`` keys (in-memory store) and the
    legacy ``dk_`` keys stored on the user row.
    """
    if api_key.startswith("sk-"):
        from app.core.api_key_store import lookup_user_id_by_key

        uid = lookup_user_id_by_key(api_key)
        if not uid:
            return None
        result = await db.execute(
            select(User).where(User.id == UUID(uid), User.is_active.is_(True))
        )
        user = result.scalar_one_or_none()
        if user is None:
            return None
        user.last_login_at = datetime.now(UTC)
        return user

    # Legacy dk_ keys stored on the user row. The stored prefix is everything
    # up to the last underscore (e.g. ``dk_abcd`` for ``dk_abcd_secret``).
    if "_" not in api_key:
        return None

    prefix = api_key.rsplit("_", 1)[0]
    if not prefix.startswith("dk_"):
        return None

    result = await db.execute(
        select(User).where(
            User.api_key_prefix == prefix,
            User.is_active.is_(True),
        )
    )
    user = result.scalar_one_or_none()

    if user and verify_user_api_key(user.api_key, api_key):
        user.last_login_at = datetime.now(UTC)
        if not is_stored_api_key_hash(user.api_key):
            user.api_key = hash_token(api_key)
            await db.commit()
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
