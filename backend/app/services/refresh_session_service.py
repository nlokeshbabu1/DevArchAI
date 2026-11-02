"""Opaque refresh-token sessions: rotation, reuse detection, and family revocation.

Refresh tokens are cryptographically random opaque strings. Only SHA-256 hashes
are stored in PostgreSQL. Redis provides short-lived rotation locks and optional
OAuth state (see oauth_state.py).
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import structlog
from fastapi import HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import decode_token, hash_token
from app.models.settings import UserSession
from app.models.user import User
from app.services.audit_logger import audit_logger

logger = structlog.get_logger(__name__)

REFRESH_ROTATE_LOCK_PREFIX = "devarchai:refresh:rotate:"
REFRESH_ROTATE_LOCK_SECONDS = 15


def generate_opaque_refresh_token() -> str:
    """Create a URL-safe opaque refresh token (never log the return value)."""
    return secrets.token_urlsafe(32)


def _looks_like_jwt(token: str) -> bool:
    parts = token.split(".")
    return len(parts) == 3 and all(parts)


async def _acquire_rotation_lock(token_hash: str) -> bool:
    """Redis SET NX lock so concurrent refreshes with the same token serialize."""
    from app.cache.redis_cache import get_cache

    try:
        cache = await get_cache()
        if not cache.is_connected or cache._redis is None:
            logger.error("refresh_rotation_lock_unavailable", reason="redis_unavailable")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable",
            )
        key = f"{REFRESH_ROTATE_LOCK_PREFIX}{token_hash[:32]}"
        acquired = await cache._redis.set(key, "1", nx=True, ex=REFRESH_ROTATE_LOCK_SECONDS)
        return bool(acquired)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("refresh_rotation_lock_failed", error_type=type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        ) from exc


async def _release_rotation_lock(token_hash: str) -> None:
    from app.cache.redis_cache import get_cache

    try:
        cache = await get_cache()
        if cache.is_connected and cache._redis is not None:
            key = f"{REFRESH_ROTATE_LOCK_PREFIX}{token_hash[:32]}"
            await cache._redis.delete(key)
    except Exception:
        pass


def parse_user_agent(user_agent: str) -> tuple[str, str, str]:
    """Parse User-Agent into browser, OS, and device class."""
    ua = user_agent or ""
    browser = "Unknown"
    os_name = "Unknown"
    device = "Unknown"

    if "Chrome" in ua and "Edge" not in ua:
        browser = "Chrome"
    elif "Firefox" in ua:
        browser = "Firefox"
    elif "Safari" in ua and "Chrome" not in ua:
        browser = "Safari"
    elif "Edge" in ua:
        browser = "Edge"

    if "Windows NT" in ua:
        os_name = "Windows"
    elif "Mac OS X" in ua or "macOS" in ua:
        os_name = "macOS"
    elif "Linux" in ua and "Android" not in ua:
        os_name = "Linux"
    elif "Android" in ua:
        os_name = "Android"
    elif "iOS" in ua or "iPhone" in ua or "iPad" in ua:
        os_name = "iOS"

    if "Mobile" in ua:
        device = "Mobile"
    elif "Tablet" in ua or "iPad" in ua:
        device = "Tablet"
    else:
        device = "Desktop"

    return browser, os_name, device


async def create_refresh_session(
    db: AsyncSession,
    user: User,
    request: Request,
    *,
    token_family: str | None = None,
    browser: str | None = None,
    os_name: str | None = None,
    device: str | None = None,
) -> tuple[UserSession, str]:
    """Persist a new refresh session and return (session, raw_opaque_token)."""
    raw = generate_opaque_refresh_token()
    ua = request.headers.get("User-Agent", "")
    if browser is None:
        browser, os_name, device = parse_user_agent(ua)

    family = token_family or str(uuid4())
    now = datetime.now(UTC)
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_token(raw),
        token_family=family,
        browser=browser,
        os=os_name,
        ip_address=request.client.host if request.client else "0.0.0.0",
        user_agent=ua,
        device_name=request.headers.get("Sec-Ch-UA-Platform", device),
        is_current=True,
        revoked=False,
        last_active_at=now,
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    await db.flush()
    return session, raw


async def _find_session_for_token(
    db: AsyncSession,
    user_id: UUID,
    raw_token: str,
    *,
    for_update: bool = False,
) -> UserSession | None:
    token_hash = hash_token(raw_token)
    stmt = select(UserSession).where(
        UserSession.user_id == user_id,
        UserSession.refresh_token_hash == token_hash,
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _resolve_user_from_legacy_jwt_refresh(
    db: AsyncSession,
    raw_token: str,
) -> tuple[User | None, UserSession | None]:
    """Support one migration path from JWT refresh cookies to opaque tokens."""
    payload = decode_token(raw_token)
    if not payload or payload.get("type") != "refresh":
        return None, None
    sub = payload.get("sub")
    if not sub:
        return None, None
    try:
        user_uuid = UUID(sub)
    except (ValueError, AttributeError):
        return None, None
    from sqlalchemy import select as sa_select

    user_result = await db.execute(sa_select(User).where(User.id == user_uuid))
    user = user_result.scalar_one_or_none()
    if not user:
        return None, None
    session = await _find_session_for_token(db, user.id, raw_token)
    return user, session


async def revoke_token_family(
    db: AsyncSession,
    user_id: UUID,
    token_family: str,
) -> None:
    await db.execute(
        update(UserSession)
        .where(
            UserSession.user_id == user_id,
            UserSession.token_family == token_family,
        )
        .values(revoked=True, is_current=False)
    )


async def rotate_refresh_session(
    db: AsyncSession,
    user: User,
    request: Request,
    raw_token: str,
) -> tuple[str, UserSession]:
    """Validate opaque refresh token, rotate, return (new_raw_token, new_session).

    Raises HTTPException on invalid, revoked, or reuse-detected tokens.
    """
    token_hash = hash_token(raw_token)
    if not await _acquire_rotation_lock(token_hash):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Refresh already in progress",
        )

    try:
        session = await _find_session_for_token(
            db, user.id, raw_token, for_update=True
        )

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        if session.expires_at and session.expires_at < datetime.now(UTC):
            session.revoked = True
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        if session.revoked:
            if session.token_family:
                logger.warning(
                    "refresh_token_reuse_detected",
                    user_id=str(user.id)[:8],
                    token_family=session.token_family,
                )
                await revoke_token_family(db, user.id, session.token_family)
                await db.commit()
                await audit_logger.log(
                    actor_id=str(user.id),
                    action="auth.token.reuse_detected",
                    resource_type="session",
                    resource_id=str(user.id),
                    details={"token_family": session.token_family},
                    ip_address=request.client.host if request.client else None,
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked. Please log in again.",
            )

        family = session.token_family or str(uuid4())
        session.revoked = True
        session.is_current = False

        new_session, new_raw = await create_refresh_session(
            db,
            user,
            request,
            token_family=family,
        )
        await db.commit()
        return new_raw, new_session
    finally:
        await _release_rotation_lock(token_hash)


async def perform_refresh_rotation(
    db: AsyncSession,
    request: Request,
    raw_token: str,
) -> tuple[User, str, UserSession]:
    """Validate refresh cookie and rotate to a new opaque token."""
    if _looks_like_jwt(raw_token):
        user, _legacy_session = await _resolve_user_from_legacy_jwt_refresh(db, raw_token)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )
        payload = decode_token(raw_token)
        old_jti = payload.get("jti") if payload else None
        if old_jti:
            from app.services.token_blacklist import BlacklistRedisError, is_blacklisted

            try:
                if await is_blacklisted(old_jti):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has been revoked",
                    )
            except BlacklistRedisError:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Service temporarily unavailable",
                )
        new_raw, new_session = await rotate_refresh_session(db, user, request, raw_token)
        if old_jti:
            from app.services.token_blacklist import blacklist_token

            await blacklist_token(old_jti, expires_in=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
        return user, new_raw, new_session

    token_hash = hash_token(raw_token)
    result = await db.execute(
        select(UserSession, User)
        .join(User, UserSession.user_id == User.id)
        .where(UserSession.refresh_token_hash == token_hash)
    )
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    _session, user = row
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    new_raw, new_session = await rotate_refresh_session(db, user, request, raw_token)
    return user, new_raw, new_session


async def resolve_user_from_refresh_cookie(
    db: AsyncSession,
    raw_token: str,
) -> User | None:
    """Resolve user from refresh cookie hash without rotating (e.g. logout)."""
    token_hash = hash_token(raw_token)
    result = await db.execute(
        select(UserSession, User)
        .join(User, UserSession.user_id == User.id)
        .where(UserSession.refresh_token_hash == token_hash)
    )
    row = result.first()
    if not row:
        return None
    _session, user = row
    if not user.is_active:
        return None
    return user


async def revoke_session_for_token(
    db: AsyncSession,
    user_id: UUID,
    raw_token: str | None,
) -> None:
    if not raw_token:
        return
    token_hash = hash_token(raw_token)
    await db.execute(
        update(UserSession)
        .where(
            UserSession.user_id == user_id,
            UserSession.refresh_token_hash == token_hash,
        )
        .values(revoked=True, is_current=False)
    )


async def revoke_all_user_sessions(
    db: AsyncSession,
    user_id: UUID,
    *,
    except_token_hash: str | None = None,
) -> int:
    stmt = update(UserSession).where(
        UserSession.user_id == user_id,
        UserSession.revoked.is_(False),
    )
    if except_token_hash:
        stmt = stmt.where(UserSession.refresh_token_hash != except_token_hash)
    result = await db.execute(stmt.values(revoked=True, is_current=False))
    return result.rowcount or 0
