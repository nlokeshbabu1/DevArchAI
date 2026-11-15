"""Account deletion confirmation helpers (provider-aware)."""

from __future__ import annotations

import httpx
import structlog
from fastapi import HTTPException, status

from app.core.encryption import get_user_oauth_token
from app.core.security import verify_password
from app.models.user import User

logger = structlog.get_logger(__name__)

DELETE_CONFIRMATION_PHRASE = "DELETE"


def user_has_usable_password(user: User) -> bool:
    """Return True when the user has a locally verifiable password hash."""
    hashed = (user.hashed_password or "").strip()
    return bool(hashed and hashed.startswith("$2"))


def user_has_github_identity(user: User) -> bool:
    return bool(
        user.github_id
        or user.github_access_token
        or user.github_access_token_encrypted
    )


def user_has_gitlab_identity(user: User) -> bool:
    return bool(
        user.gitlab_id
        or user.gitlab_access_token
        or user.gitlab_access_token_encrypted
    )


async def verify_github_identity_active(user: User) -> None:
    """Confirm stored GitHub OAuth token still matches the linked GitHub user."""
    if not user.github_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub is not linked to this account.",
        )
    token = get_user_oauth_token(user, "github")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub session expired. Reconnect GitHub in Integrations, then try again.",
        )
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                timeout=15.0,
            )
    except httpx.RequestError as exc:
        logger.warning("github_delete_verify_failed", user_id=str(user.id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not verify GitHub identity. Try again later.",
        ) from exc

    if response.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub session expired. Reconnect GitHub in Integrations, then try again.",
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub identity verification failed.",
        )

    remote_id = str(response.json().get("id", ""))
    if remote_id != str(user.github_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub identity no longer matches this account.",
        )


async def verify_gitlab_identity_active(user: User) -> None:
    """Confirm stored GitLab OAuth token still matches the linked GitLab user."""
    if not user.gitlab_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitLab is not linked to this account.",
        )
    token = get_user_oauth_token(user, "gitlab")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitLab session expired. Reconnect GitLab in Integrations, then try again.",
        )
    base = "https://gitlab.com"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base}/api/v4/user",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15.0,
            )
    except httpx.RequestError as exc:
        logger.warning("gitlab_delete_verify_failed", user_id=str(user.id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not verify GitLab identity. Try again later.",
        ) from exc

    if response.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitLab session expired. Reconnect GitLab in Integrations, then try again.",
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitLab identity verification failed.",
        )

    remote_id = str(response.json().get("id", ""))
    if remote_id != str(user.gitlab_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitLab identity no longer matches this account.",
        )


async def assert_account_deletion_allowed(
    user: User,
    *,
    password: str | None,
    confirmation: str | None,
    provider: str | None,
) -> None:
    """Enforce provider-aware reauthentication before account deletion."""
    has_password = user_has_usable_password(user)
    has_github = user_has_github_identity(user)
    has_gitlab = user_has_gitlab_identity(user)

    if has_password:
        if not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required",
            )
        if not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is incorrect",
            )
        return

    if confirmation != DELETE_CONFIRMATION_PHRASE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Type "{DELETE_CONFIRMATION_PHRASE}" to confirm account deletion',
        )

    normalized = (provider or "").lower()
    if normalized == "github":
        if not has_github:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub is not linked to this account.",
            )
        await verify_github_identity_active(user)
        return

    if normalized == "gitlab":
        if not has_gitlab:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitLab is not linked to this account.",
            )
        await verify_gitlab_identity_active(user)
        return

    if has_github:
        await verify_github_identity_active(user)
        return
    if has_gitlab:
        await verify_gitlab_identity_active(user)
        return

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Set a password in Settings or link GitHub/GitLab before deleting this account.",
    )