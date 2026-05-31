"""Authentication routes with enterprise-grade security.

Supports:
- Email/password login (unchanged)
- GitHub OAuth (unchanged)
- Refresh token rotation
- HttpOnly cookie-based refresh tokens
- Session management
- Token blacklisting
- Audit logging
"""

import uuid
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_user_email,
    encrypt_user_email,
    generate_api_key,
    get_current_user,
    get_password_hash,
    hash_email,
    hash_token,
    verify_password,
)
from app.db.session import get_db
from app.models.settings import UserSession
from app.models.user import User
from app.schemas.auth import (
    APIKeyResponse,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.schemas.common import MessageResponse
from app.schemas.enterprise_auth import LogoutResponse, RevokeAllSessionsResponse, SessionResponse
from app.services.audit_logger import audit_logger
from app.services.organization_provisioning import ensure_user_organization_membership
from app.services.token_blacklist import blacklist_token

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


def _safe_email(user: User) -> str:
    """Safely return a user's email. Never exposes encrypted blob."""
    if not user.email_encrypted:
        return "Email unavailable"
    if "@" in user.email_encrypted:
        return user.email_encrypted
    try:
        decrypted = decrypt_user_email(user.email_encrypted)
        if "@" in decrypted:
            return decrypted
    except Exception as e:
        logger.warning("user_to_response email decrypt failed for user_id=%s: %s", user.id, e)
    return f"{user.username}@email.local"


def user_to_response(user: User) -> dict:
    """Convert User model to response dict with proper UUID serialization."""
    email = _safe_email(user)
    
    return {
        "id": str(user.id) if isinstance(user.id, uuid.UUID) else user.id,
        "email": email,
        "username": user.username,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "has_api_key": bool(user.api_key),
        "plan": user.subscription_plan if hasattr(user, 'subscription_plan') else "free",
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user and create their organization."""
    logger.info("Register attempt", username=user_data.username)

    # Check if email already exists (using hash)
    email_hash = hash_email(user_data.email)
    result = await db.execute(select(User).where(User.email_hash == email_hash))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if username already exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    try:
        # Encrypt email and create hash
        email_encrypted, email_hash = encrypt_user_email(user_data.email)

        # Create user with encrypted email
        user = User(
            email_encrypted=email_encrypted,
            email_hash=email_hash,
            username=user_data.username,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            country=user_data.country or "US",
        )
        db.add(user)
        await db.flush()  # Get user ID
        logger.info("User created", user_id=user.id)

        await ensure_user_organization_membership(
            db,
            user,
            organization_name=user_data.organization_name,
        )

        await db.commit()
        await db.refresh(user)
        logger.info("Registration completed", user_id=user.id)

        # Return dict directly to avoid Pydantic validation issues
        return user_to_response(user)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Registration failed", error=str(e), email=user_data.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )

def _parse_user_agent(user_agent: str) -> tuple[str, str, str]:
    """Parse User-Agent to extract browser, OS, and device name."""
    ua = user_agent or ""
    browser = "Unknown"
    os = "Unknown"
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
        os = "Windows"
    elif "Mac OS X" in ua or "macOS" in ua:
        os = "macOS"
    elif "Linux" in ua and "Android" not in ua:
        os = "Linux"
    elif "Android" in ua:
        os = "Android"
    elif "iOS" in ua or "iPhone" in ua or "iPad" in ua:
        os = "iOS"
    elif "CrOS" in ua:
        os = "ChromeOS"

    if "Mobile" in ua:
        device = "Mobile"
    elif "Tablet" in ua or "iPad" in ua:
        device = "Tablet"
    else:
        device = "Desktop"

    return browser, os, device


async def _detect_new_device(
    db: AsyncSession, user: User, browser: str, os: str, ip_address: str
) -> bool:
    """Check if this is a new device/browser/IP for the user."""
    try:
        result = await db.execute(
            select(UserSession).where(
                UserSession.user_id == user.id,
                UserSession.revoked.is_(False),
            ).limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            return True
        if existing.ip_address != ip_address:
            return True
        if existing.browser != browser:
            return True
        if existing.os != os:
            return True
        return False
    except Exception:
        return False


def _should_include_refresh_token_body() -> bool:
    """Check if refresh token should be included in response body."""
    return settings.AUTH_REFRESH_TOKEN_STORAGE_MODE in ("legacy", "hybrid")


def _is_cookie_only_mode() -> bool:
    """Check if we are in cookie-only mode."""
    return settings.AUTH_REFRESH_TOKEN_STORAGE_MODE == "cookie_only"


def _warn_if_local_storage_used(request: Request) -> None:
    """Log warning if refresh token is read from Authorization header (localStorage)."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer ") and not request.cookies.get("refresh_token"):
        logger.warning(
            "Refresh token read from Authorization header (localStorage)",
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )


async def _create_session(
    db: AsyncSession, user: User, request: Request, refresh_token: str
) -> UserSession:
    """Create a user session record."""
    user_agent = request.headers.get("User-Agent", "")
    ip_address = request.client.host if request.client else "0.0.0.0"
    browser, os, device = _parse_user_agent(user_agent)

    session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_token(refresh_token),
        browser=browser,
        os=os,
        ip_address=ip_address,
        user_agent=user_agent,
        device_name=request.headers.get("Sec-Ch-UA-Platform", device),
        is_current=True,
        expires_at=datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    await db.flush()
    return session


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Set refresh token as HttpOnly secure cookie."""
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
    )


async def _check_account_locked(user: User) -> None:
    """Check if account is locked due to too many failed attempts."""
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        remaining = int((user.locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account is locked. Try again in {remaining} minutes.",
        )


def _enrich_jwt_claims(user: User) -> dict[str, Any]:
    """Add role, permissions, and org_id to JWT claims."""
    claims = {"sub": str(user.id), "email": _safe_email(user)}
    claims["role"] = user.role.value if hasattr(user.role, "value") else str(user.role)
    claims["org_id"] = str(user.current_org_id) if user.current_org_id else None
    try:
        from app.services.rbac import get_user_permissions
        perms = get_user_permissions(user)
        claims["permissions"] = list(perms)
    except Exception:
        claims["permissions"] = []
    return claims


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT tokens."""
    email_hash = hash_email(credentials.email)
    result = await db.execute(select(User).where(User.email_hash == email_hash))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
                await db.commit()
            else:
                await db.commit()
        await audit_logger.log(
            action="auth.login.failed",
            resource_type="user",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            details={"reason": "invalid_credentials", "email": credentials.email},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await _check_account_locked(user)

    if not user.is_active:
        await audit_logger.log(
            actor_id=str(user.id),
            action="auth.login.blocked",
            resource_type="user",
            resource_id=str(user.id),
            ip_address=request.client.host if request.client else None,
            details={"reason": "account_disabled"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    await ensure_user_organization_membership(db, user)
    await db.flush()

    # Enriched JWT with role, permissions, org_id
    claims = _enrich_jwt_claims(user)
    access_token = create_access_token(data=claims)
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    browser, os_val, device = _parse_user_agent(request.headers.get("User-Agent", ""))

    # Check for new device login
    is_new_device = await _detect_new_device(db, user, browser, os_val, request.client.host if request.client else "")
    if is_new_device:
        await audit_logger.log(
            actor_id=str(user.id),
            action="auth.new_device_login",
            resource_type="session",
            resource_id=str(user.id),
            details={"browser": browser, "os": os_val, "device": device},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )

    session = await _create_session(db, user, request, refresh_token)
    await db.commit()

    _set_refresh_cookie(response, refresh_token)

    await audit_logger.log(
        actor_id=str(user.id),
        action="auth.login.success",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token if _should_include_refresh_token_body() else None,
    )


@router.get("/github/url")
async def get_github_oauth_url(redirect_uri: str | None = None):
    """
    Get GitHub OAuth authorization URL.

    Returns the URL to redirect users to for GitHub OAuth authentication.
    Uses redirect_uri from query param if provided, otherwise uses settings.
    """
    if not settings.GITHUB_CLIENT_ID:
        # Return a mock URL for development/testing
        # In production, this should return actual OAuth URL
        return {
            "oauth_url": None,
            "error": "GitHub OAuth not configured",
            "message": "Please use email/password authentication"
        }

    # Use redirect_uri from query param if provided, otherwise use settings
    final_redirect_uri = redirect_uri or settings.GITHUB_REDIRECT_URI

    # Build OAuth URL
    oauth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope=user:email%20read:user%20repo"
    )

    logger.info("Generated GitHub OAuth URL", redirect_uri=final_redirect_uri)
    return {"oauth_url": oauth_url}


@router.post("/github/callback")
async def github_callback(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    GitHub OAuth callback endpoint.

    Exchanges GitHub authorization code for access token,
    gets user info, and creates/updates user in database.
    """
    try:
        # Get authorization code from request
        data = await request.json()
        code = data.get("code")

        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code required",
            )

        # Validate GitHub OAuth settings
        if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
            logger.error("GitHub OAuth not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GitHub OAuth not configured on server",
            )

        # Exchange code for access token
        token_url = "https://github.com/login/oauth/access_token"
        token_data = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.GITHUB_REDIRECT_URI,
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_url,
                data=token_data,
                headers={"Accept": "application/json"},
                timeout=10.0,
            )

            if token_response.status_code != 200:
                logger.error("GitHub token exchange failed", status=token_response.status_code)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange authorization code",
                )

            token_json = token_response.json()
            github_access_token = token_json.get("access_token")

            if not github_access_token:
                logger.error("No access token in GitHub response", response=token_json)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from GitHub",
                )

            # Get user info from GitHub
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"token {github_access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                timeout=10.0,
            )

            if user_response.status_code != 200:
                logger.error("GitHub user info fetch failed", status=user_response.status_code)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch GitHub user info",
                )

            github_user = user_response.json()

            # Extract user information
            github_id = str(github_user.get("id"))
            email = github_user.get("email")
            username = github_user.get("login")
            full_name = github_user.get("name", "")
            avatar_url = github_user.get("avatar_url", "")

            # If no email from GitHub, fetch it
            if not email:
                emails_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"token {github_access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                    timeout=10.0,
                )

                if emails_response.status_code == 200:
                    emails = emails_response.json()
                    # Get primary email
                    for email_data in emails:
                        if email_data.get("primary"):
                            email = email_data.get("email")
                            break

            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No email found in GitHub account",
                )

            # Find or create user in database using email hash
            email_hash = hash_email(email)
            result = await db.execute(select(User).where(User.email_hash == email_hash))
            user = result.scalar_one_or_none()

            if not user:
                # Encrypt email and create hash
                email_encrypted, email_hash = encrypt_user_email(email)

                # Create new user
                user = User(
                    email_encrypted=email_encrypted,
                    email_hash=email_hash,
                    username=username or email.split("@")[0],
                    hashed_password="",  # No password for OAuth users
                    full_name=full_name or "",
                    avatar_url=avatar_url or "",
                    github_id=github_id,
                    github_login=username,  # Store GitHub username for webhook lookups
                    github_access_token=github_access_token,  # Store GitHub token for API access
                    is_verified=True,  # GitHub emails are verified
                )
                db.add(user)
                await db.flush()
                logger.info("User created from GitHub OAuth", user_id=user.id)
            else:
                # Update existing user with GitHub info
                user.github_id = github_id
                user.github_login = username  # Store/update GitHub username
                user.github_access_token = github_access_token  # Update token
                if avatar_url:
                    user.avatar_url = avatar_url
                if full_name and not user.full_name:
                    user.full_name = full_name

            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login_at = datetime.now(timezone.utc)
            await ensure_user_organization_membership(db, user)
            await db.flush()

            # Enriched JWT claims
            claims = _enrich_jwt_claims(user)
            access_token_jwt = create_access_token(data=claims)
            refresh_token_jwt = create_refresh_token(data={"sub": str(user.id)})

            browser, os_val, device = _parse_user_agent(request.headers.get("User-Agent", ""))

            is_new_device = await _detect_new_device(db, user, browser, os_val, request.client.host if request.client else "")
            if is_new_device:
                await audit_logger.log(
                    actor_id=str(user.id),
                    action="auth.new_device_login",
                    resource_type="session",
                    resource_id=str(user.id),
                    details={"browser": browser, "os": os_val, "device": device, "provider": "github"},
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("User-Agent"),
                )

            session = await _create_session(db, user, request, refresh_token_jwt)
            await db.commit()
            await db.refresh(user)

            _set_refresh_cookie(response, refresh_token_jwt)

            await audit_logger.log(
                actor_id=str(user.id),
                action="auth.github.login.success",
                resource_type="user",
                resource_id=str(user.id),
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            )

            logger.info("GitHub OAuth successful", user_id=user.id)

            resp = {
                "access_token": access_token_jwt,
                "token_type": "bearer",
                "user": user_to_response(user),
            }
            if _should_include_refresh_token_body():
                resp["refresh_token"] = refresh_token_jwt
            return resp

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("GitHub OAuth callback failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GitHub OAuth failed: {str(e)}",
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Logout current user: blacklist tokens, revoke session, clear cookie."""
    raw_token = request.cookies.get("refresh_token")
    if not raw_token and not _is_cookie_only_mode():
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header.replace("Bearer ", "")
            _warn_if_local_storage_used(request)

    token_hash = hash_token(raw_token) if raw_token else None

    # Blacklist current access token if we can extract jti
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        access_token_str = auth_header.replace("Bearer ", "")
        access_payload = decode_token(access_token_str)
        if access_payload and access_payload.get("jti"):
            await blacklist_token(access_payload["jti"])

    # Blacklist refresh token
    if raw_token:
        refresh_payload = decode_token(raw_token)
        if refresh_payload and refresh_payload.get("jti"):
            await blacklist_token(
                refresh_payload["jti"],
                expires_in=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            )

    # Revoke session
    if token_hash:
        await db.execute(
            update(UserSession)
            .where(
                UserSession.user_id == current_user.id,
                UserSession.refresh_token_hash == token_hash,
            )
            .values(revoked=True, is_current=False)
        )
        await db.commit()

    # Clear cookie
    response.delete_cookie(
        key="refresh_token",
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
    )

    await audit_logger.log(
        actor_id=str(current_user.id),
        action="auth.logout",
        resource_type="user",
        resource_id=str(current_user.id),
        ip_address=request.client.host if request.client else None,
    )

    return LogoutResponse()


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active sessions for the current user."""
    result = await db.execute(
        select(UserSession)
        .where(
            UserSession.user_id == current_user.id,
            UserSession.revoked.is_(False),
        )
        .order_by(UserSession.last_active_at.desc())
    )
    sessions = result.scalars().all()

    # Determine current session from cookie/header
    raw_token = request.cookies.get("refresh_token")
    if not raw_token and not _is_cookie_only_mode():
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header.replace("Bearer ", "")
            _warn_if_local_storage_used(request)
    
    current_token_hash = hash_token(raw_token) if raw_token else None

    session_list = []
    for s in sessions:
        is_current = bool(
            current_token_hash and s.refresh_token_hash == current_token_hash
        )
        session_list.append(SessionResponse(
            id=str(s.id),
            device_name=s.device_name,
            browser=s.browser,
            os=s.os,
            ip_address=s.ip_address,
            location=s.location,
            created_at=s.created_at,
            last_active_at=s.last_active_at,
            expires_at=s.expires_at,
            is_current=is_current,
        ))
    return session_list


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a specific session."""
    try:
        from uuid import UUID as UUIDType
        session_uuid = UUIDType(session_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID",
        )

    result = await db.execute(
        select(UserSession).where(
            UserSession.id == session_uuid,
            UserSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session.revoked = True
    session.is_current = False
    await db.commit()

    await audit_logger.log(
        actor_id=str(current_user.id),
        action="auth.session.revoke",
        resource_type="session",
        resource_id=str(session.id),
        ip_address=request.client.host if request.client else None,
    )

    return MessageResponse(message="Session revoked successfully")


@router.post("/revoke-all", response_model=RevokeAllSessionsResponse)
async def revoke_all_sessions(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke all sessions except the current one."""
    # Determine current session
    raw_token = request.cookies.get("refresh_token")
    if not raw_token and not _is_cookie_only_mode():
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header.replace("Bearer ", "")
            _warn_if_local_storage_used(request)

    current_token_hash = hash_token(raw_token) if raw_token else None

    # Revoke all non-current sessions
    if current_token_hash:
        result = await db.execute(
            update(UserSession)
            .where(
                UserSession.user_id == current_user.id,
                UserSession.refresh_token_hash != current_token_hash,
                UserSession.revoked.is_(False),
            )
            .values(revoked=True, is_current=False)
        )
    else:
        result = await db.execute(
            update(UserSession)
            .where(
                UserSession.user_id == current_user.id,
                UserSession.revoked.is_(False),
            )
            .values(revoked=True, is_current=False)
        )

    revoked_count = result.rowcount if result else 0
    await db.commit()

    await audit_logger.log(
        actor_id=str(current_user.id),
        action="auth.sessions.revoke_all",
        resource_type="user",
        resource_id=str(current_user.id),
        details={"revoked_count": revoked_count},
        ip_address=request.client.host if request.client else None,
    )

    return RevokeAllSessionsResponse(
        message=f"Revoked {revoked_count} session(s)",
        revoked_count=revoked_count,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current user information."""
    return user_to_response(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile."""
    # Update fields
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    if user_data.avatar_url is not None:
        current_user.avatar_url = user_data.avatar_url

    # Update password if provided
    if user_data.new_password:
        if not user_data.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password required to set new password",
            )

        if not verify_password(user_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        current_user.hashed_password = get_password_hash(user_data.new_password)

    await db.commit()
    await db.refresh(current_user)

    return user_to_response(current_user)


@router.post("/api-key", response_model=APIKeyResponse)
async def create_api_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new API key for the current user."""
    api_key, prefix = generate_api_key()

    current_user.api_key = api_key
    current_user.api_key_prefix = prefix

    await db.commit()

    return APIKeyResponse(
        api_key=api_key,
        api_key_prefix=prefix,
        created_at=datetime.now(UTC),
    )


@router.delete("/api-key", response_model=MessageResponse)
async def revoke_api_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the current API key."""
    current_user.api_key = None
    current_user.api_key_prefix = None

    await db.commit()

    return MessageResponse(message="API key revoked successfully")


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token with rotation.

    Validates the refresh token, blacklists the old one,
    issues new tokens, and creates a new session.
    """
    # Try cookie first, then Authorization header (unless cookie_only mode)
    raw_token = request.cookies.get("refresh_token")
    if not raw_token and not _is_cookie_only_mode():
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header.replace("Bearer ", "")
            _warn_if_local_storage_used(request)

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    payload = decode_token(raw_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Check blacklist
    old_jti = payload.get("jti")
    if old_jti:
        from app.services.token_blacklist import is_blacklisted
        if await is_blacklisted(old_jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Get user
    try:
        from uuid import UUID
        user_uuid = UUID(user_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Warn if reading from localStorage (Authorization header)
    _warn_if_local_storage_used(request)

    email = decrypt_user_email(user.email_encrypted)

    # Enriched JWT claims
    claims = _enrich_jwt_claims(user)
    new_access_token = create_access_token(data=claims)
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # Blacklist old refresh token
    if old_jti:
        await blacklist_token(
            old_jti,
            expires_in=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

    # Revoke old sessions with this token hash
    old_token_hash = hash_token(raw_token)
    await db.execute(
        update(UserSession)
        .where(
            UserSession.user_id == user.id,
            UserSession.refresh_token_hash == old_token_hash,
        )
        .values(revoked=True, is_current=False)
    )

    # Create new session
    new_session = await _create_session(db, user, request, new_refresh_token)
    await db.commit()

    _set_refresh_cookie(response, new_refresh_token)

    await audit_logger.log(
        actor_id=str(user.id),
        action="auth.token.refresh",
        resource_type="session",
        resource_id=str(new_session.id),
        ip_address=request.client.host if request.client else None,
    )

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token if _should_include_refresh_token_body() else None,
    )
