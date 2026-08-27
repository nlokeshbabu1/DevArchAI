"""GitLab OAuth authentication routes."""

import time
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routes.auth import _parse_user_agent, _should_include_refresh_token_body
from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decrypt_user_email,
    encrypt_user_email,
    hash_email,
    hash_token,
)
from app.db.session import get_db
from app.models.settings import UserSession
from app.models.user import User
from app.services.audit_logger import audit_logger
from app.services.organization_provisioning import ensure_user_organization_membership

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

_oauth_states: dict[str, float] = {}
_OAUTH_STATE_TTL = 600


def _generate_state() -> str:
    state = uuid.uuid4().hex
    _oauth_states[state] = time.time()
    return state


def _validate_state(state: str) -> bool:
    now = time.time()
    if state in _oauth_states:
        created_at = _oauth_states.pop(state)
        if now - created_at < _OAUTH_STATE_TTL:
            return True
    _clean_expired_states(now)
    return False


def _clean_expired_states(now: float | None = None) -> None:
    if now is None:
        now = time.time()
    expired = [s for s, t in _oauth_states.items() if now - t >= _OAUTH_STATE_TTL]
    for s in expired:
        _oauth_states.pop(s, None)


def _safe_email(user: User) -> str:
    if not user.email_encrypted:
        return "Email unavailable"
    if "@" in user.email_encrypted:
        return user.email_encrypted
    try:
        decrypted = decrypt_user_email(user.email_encrypted)
        if "@" in decrypted:
            return decrypted
    except Exception:
        pass
    return f"{user.username}@email.local"


def user_to_response(user: User) -> dict:
    email = _safe_email(user)
    return {
        "id": str(user.id) if isinstance(user.id, uuid.UUID) else user.id,
        "email": email,
        "username": user.username,
        "avatar_url": user.avatar_url or "",
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "role": user.role.value if hasattr(user.role, "value") else user.role,
        "current_org_id": str(user.current_org_id) if user.current_org_id else None,
        "has_github": bool(user.github_id or user.github_access_token or user.github_access_token_encrypted),
        "has_gitlab": bool(user.gitlab_id or user.gitlab_access_token or user.gitlab_access_token_encrypted),
        "provider": "github" if user.github_id or user.github_access_token or user.github_access_token_encrypted else "gitlab" if user.gitlab_id or user.gitlab_access_token or user.gitlab_access_token_encrypted else "password",
    }


@router.get("/gitlab/url")
async def get_gitlab_oauth_url(redirect_uri: str | None = None):
    """Get GitLab OAuth authorization URL."""
    if not settings.GITLAB_CLIENT_ID:
        logger.warning("GitLab OAuth not configured")
        return {
            "oauth_url": None,
            "error": "GitLab OAuth not configured",
            "message": "Please use email/password authentication"
        }

    final_redirect_uri = redirect_uri or settings.GITLAB_REDIRECT_URI
    gitlab_url = settings.GITLAB_URL.rstrip("/")
    state = _generate_state()

    params = urlencode({
        "client_id": settings.GITLAB_CLIENT_ID,
        "redirect_uri": final_redirect_uri,
        "response_type": "code",
        "scope": "read_user api",
        "state": state,
    })

    oauth_url = f"{gitlab_url}/oauth/authorize?{params}"

    logger.info("Generated GitLab OAuth URL state", state=state)
    return {"oauth_url": oauth_url, "state": state}


@router.post("/gitlab/callback")
async def gitlab_callback(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """GitLab OAuth callback endpoint."""
    try:
        try:
            data = await request.json()
        except Exception as exc:  # invalid/empty JSON body
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request body must be valid JSON",
            ) from exc
        code = data.get("code")
        state = data.get("state")

        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code required",
            )

        if state and not _validate_state(state):
            logger.warning("Invalid or expired OAuth state", state=state)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OAuth state. Please try again.",
            )

        if not settings.GITLAB_CLIENT_ID or not settings.GITLAB_CLIENT_SECRET:
            logger.error("GitLab OAuth not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GitLab OAuth not configured on server",
            )

        gitlab_url = settings.GITLAB_URL.rstrip("/")
        redirect_uri = settings.GITLAB_REDIRECT_URI

        async with httpx.AsyncClient() as client:
            # Exchange code for access token
            token_response = await client.post(
                f"{gitlab_url}/oauth/token",
                data=urlencode({
                    "client_id": settings.GITLAB_CLIENT_ID,
                    "client_secret": settings.GITLAB_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                }),
                headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )

            if token_response.status_code != 200:
                logger.error("GitLab token exchange failed", status=token_response.status_code)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange authorization code",
                )

            token_json = token_response.json()
            gitlab_access_token = token_json.get("access_token")

            if not gitlab_access_token:
                logger.error("No access token in GitLab response", response=token_json)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from GitLab",
                )

            # Get user info from GitLab
            user_response = await client.get(
                f"{gitlab_url}/api/v4/user",
                headers={
                    "Authorization": f"Bearer {gitlab_access_token}",
                },
                timeout=10.0,
            )

            if user_response.status_code != 200:
                logger.error("GitLab user info fetch failed", status=user_response.status_code)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch GitLab user info",
                )

            gitlab_user = user_response.json()

            gitlab_id = str(gitlab_user.get("id"))
            email = gitlab_user.get("email")
            username = gitlab_user.get("username")
            full_name = gitlab_user.get("name", "")
            avatar_url = gitlab_user.get("avatar_url", "")

            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No email found in GitLab account",
                )

            # Find or create user — check gitlab_id first, then email_hash
            result = await db.execute(select(User).where(User.gitlab_id == gitlab_id))
            user = result.scalar_one_or_none()

            if not user:
                email_hash = hash_email(email)
                result = await db.execute(select(User).where(User.email_hash == email_hash))
                user = result.scalar_one_or_none()

            if not user:
                email_encrypted, email_hash = encrypt_user_email(email)

                user = User(
                    email_encrypted=email_encrypted,
                    email_hash=email_hash,
                    username=username or email.split("@")[0],
                    hashed_password="",
                    full_name=full_name or "",
                    avatar_url=avatar_url or "",
                    gitlab_id=gitlab_id,
                    gitlab_username=username,
                    is_verified=True,
                )
                # Store encrypted GitLab token
                from app.core.encryption import set_user_oauth_token
                set_user_oauth_token(user, "gitlab", gitlab_access_token)
                db.add(user)
                await db.flush()
                logger.info("User created from GitLab OAuth", user_id=user.id)
            else:
                user.gitlab_id = gitlab_id
                user.gitlab_username = username
                # Store encrypted GitLab token
                from app.core.encryption import set_user_oauth_token
                set_user_oauth_token(user, "gitlab", gitlab_access_token)
                if avatar_url:
                    user.avatar_url = avatar_url
                if full_name and not user.full_name:
                    user.full_name = full_name

            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login_at = datetime.now(UTC)
            await ensure_user_organization_membership(db, user)
            await db.flush()

            access_token_jwt = create_access_token(data={
                "sub": str(user.id),
                "email": _safe_email(user),
                "role": user.role.value if hasattr(user.role, "value") else "user",
                "org_id": str(user.current_org_id) if user.current_org_id else None,
            })
            refresh_token_jwt = create_refresh_token(data={"sub": str(user.id)})

            # Create session with token family for reuse detection
            token_family = str(uuid.uuid4())
            user_agent_str = request.headers.get("User-Agent", "")
            ip = request.client.host if request.client else "0.0.0.0"
            browser, os_val, device = _parse_user_agent(user_agent_str)
            session = UserSession(
                user_id=user.id,
                refresh_token_hash=hash_token(refresh_token_jwt),
                token_family=token_family,
                browser=browser,
                os=os_val,
                ip_address=ip,
                user_agent=user_agent_str,
                device_name=request.headers.get("Sec-Ch-UA-Platform", device),
                is_current=True,
                expires_at=datetime.now(UTC).replace(hour=0, minute=0, second=0)
                + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            )
            db.add(session)
            await db.commit()
            await db.refresh(user)

            _set_refresh_cookie(response, refresh_token_jwt)

            await audit_logger.log(
                actor_id=str(user.id),
                action="auth.gitlab.login.success",
                resource_type="user",
                resource_id=str(user.id),
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            )

            logger.info("GitLab OAuth successful", user_id=user.id)

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
    except Exception:
        logger.exception("GitLab OAuth callback failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitLab OAuth failed. Please try again.",
        )


def _set_refresh_cookie(response: Response, token: str) -> None:
    from app.config import settings
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path=settings.COOKIE_PATH,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
