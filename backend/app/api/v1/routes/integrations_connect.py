"""Integration connection routes (OAuth connect for an already-authenticated user).

These endpoints let an authenticated DevArchAI user attach an external provider
(GitHub / GitLab) to their existing account WITHOUT switching login identity or
creating a new session. They are intentionally separate from the login OAuth
flows in auth.py / gitlab_auth.py.
"""

from __future__ import annotations

import time
import uuid

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.encryption import set_user_oauth_token
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.github_installation import GitHubInstallation
from app.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/integrations", tags=["Integrations"])

_oauth_states: dict[str, float] = {}
_OAUTH_STATE_TTL = 600


def _generate_state() -> str:
    state = uuid.uuid4().hex
    _oauth_states[state] = time.time()
    return state


def _validate_state(state: str) -> bool:
    now = time.time()
    created_at = _oauth_states.pop(state, None)
    if created_at is not None and now - created_at < _OAUTH_STATE_TTL:
        return True
    expired = [s for s, t in _oauth_states.items() if now - t >= _OAUTH_STATE_TTL]
    for s in expired:
        _oauth_states.pop(s, None)
    return False


# ── GitHub ──


@router.get("/github/url")
async def get_github_integration_url(
    user: User = Depends(get_current_user),
):
    """Get a GitHub OAuth authorization URL for attaching to the current user."""
    if not settings.GITHUB_CLIENT_ID:
        return {
            "oauth_url": None,
            "error": "GitHub OAuth not configured",
            "message": "Please use email/password authentication",
        }

    state = _generate_state()
    redirect_uri = f"{settings.FRONTEND_URL.rstrip('/')}/integrations/github/callback"
    oauth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        f"&scope=user:email%20read:user%20repo"
    )
    return {"oauth_url": oauth_url, "state": state}


@router.post("/github/callback")
async def github_integration_callback(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exchange a GitHub OAuth code and attach the identity to the current user."""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body")

    code = data.get("code")
    state = data.get("state")

    if not code:
        raise HTTPException(status_code=400, detail="Authorization code required")
    if state and not _validate_state(state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state. Please try again.")
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{settings.FRONTEND_URL.rstrip('/')}/integrations/github/callback",
            },
            headers={"Accept": "application/json"},
            timeout=10.0,
        )
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

        token_json = token_response.json()
        github_access_token = token_json.get("access_token")
        if not github_access_token:
            raise HTTPException(status_code=400, detail="No access token received from GitHub")

        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {github_access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=10.0,
        )
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch GitHub user info")

        github_user = user_response.json()
        github_id = str(github_user.get("id"))
        github_login = github_user.get("login")
        avatar_url = github_user.get("avatar_url", "")

    # Attach the identity to the *current* authenticated user (no identity switch).
    user.github_id = github_id
    user.github_login = github_login
    set_user_oauth_token(user, "github", github_access_token)
    if avatar_url:
        user.avatar_url = avatar_url

    await db.commit()

    logger.info("integration_github_connected", user_id=str(user.id), github_login=github_login)

    return {
        "connected": True,
        "provider": "github",
        "account": github_login,
        "has_github": True,
    }


@router.post("/github/disconnect")
async def github_integration_disconnect(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove the GitHub integration from the current user."""
    user.github_id = None
    user.github_login = None
    user.github_access_token = None
    user.github_access_token_encrypted = None

    # Remove any app-installation records for this user. The status endpoint
    # treats a leftover GitHubInstallation row as "connected", so leaving them
    # behind makes GitHub appear Connected even after disconnect.
    await db.execute(
        delete(GitHubInstallation).where(GitHubInstallation.user_id == user.id)
    )

    await db.commit()

    logger.info("integration_github_disconnected", user_id=str(user.id))

    return {"connected": False, "provider": "github"}


# ── GitLab ──


@router.get("/gitlab/url")
async def get_gitlab_integration_url(
    user: User = Depends(get_current_user),
):
    """Get a GitLab OAuth authorization URL for attaching to the current user."""
    if not settings.GITLAB_CLIENT_ID:
        return {
            "oauth_url": None,
            "error": "GitLab OAuth not configured",
            "message": "Please use email/password authentication",
        }

    gitlab_url = settings.GITLAB_URL.rstrip("/")
    state = _generate_state()
    redirect_uri = f"{settings.FRONTEND_URL.rstrip('/')}/integrations/gitlab/callback"
    oauth_url = (
        f"{gitlab_url}/oauth/authorize"
        f"?client_id={settings.GITLAB_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=read_user%20api"
        f"&state={state}"
    )
    return {"oauth_url": oauth_url, "state": state}


@router.post("/gitlab/callback")
async def gitlab_integration_callback(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exchange a GitLab OAuth code and attach the identity to the current user."""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    code = data.get("code")
    state = data.get("state")

    if not code:
        raise HTTPException(status_code=400, detail="Authorization code required")
    if state and not _validate_state(state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state. Please try again.")
    if not settings.GITLAB_CLIENT_ID or not settings.GITLAB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitLab OAuth not configured")

    gitlab_url = settings.GITLAB_URL.rstrip("/")

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            f"{gitlab_url}/oauth/token",
            data={
                "client_id": settings.GITLAB_CLIENT_ID,
                "client_secret": settings.GITLAB_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": f"{settings.FRONTEND_URL.rstrip('/')}/integrations/gitlab/callback",
            },
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

        token_json = token_response.json()
        gitlab_access_token = token_json.get("access_token")
        if not gitlab_access_token:
            raise HTTPException(status_code=400, detail="No access token received from GitLab")

        user_response = await client.get(
            f"{gitlab_url}/api/v4/user",
            headers={"Authorization": f"Bearer {gitlab_access_token}"},
            timeout=10.0,
        )
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch GitLab user info")

        gitlab_user = user_response.json()
        gitlab_id = str(gitlab_user.get("id"))
        gitlab_username = gitlab_user.get("username")
        avatar_url = gitlab_user.get("avatar_url", "")

    user.gitlab_id = gitlab_id
    user.gitlab_username = gitlab_username
    set_user_oauth_token(user, "gitlab", gitlab_access_token)
    if avatar_url:
        user.avatar_url = avatar_url

    await db.commit()

    logger.info("integration_gitlab_connected", user_id=str(user.id), gitlab_username=gitlab_username)

    return {
        "connected": True,
        "provider": "gitlab",
        "account": gitlab_username,
        "has_gitlab": True,
    }


@router.post("/gitlab/disconnect")
async def gitlab_integration_disconnect(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove the GitLab integration from the current user."""
    user.gitlab_id = None
    user.gitlab_username = None
    user.gitlab_access_token = None
    user.gitlab_access_token_encrypted = None
    await db.commit()

    logger.info("integration_gitlab_disconnected", user_id=str(user.id))

    return {"connected": False, "provider": "gitlab"}
