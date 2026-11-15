"""CLI browser login: PKCE authorization code with loopback redirect."""

from __future__ import annotations

from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routes.auth import _enrich_jwt_claims, user_to_response
from app.config import settings
from app.core.security import create_access_token, get_current_user, hash_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.cli_auth import (
    CliAuthApproveRequest,
    CliAuthApproveResponse,
    CliAuthRefreshRequest,
    CliAuthRegisterRequest,
    CliAuthRegisterResponse,
    CliAuthRevokeRequest,
    CliAuthTokenRequest,
    CliAuthTokenResponse,
)
from app.services.cli_auth_service import (
    approve_cli_session,
    consume_code,
    register_cli_session,
    verify_pkce,
)
from app.services.refresh_session_service import (
    create_refresh_session,
    perform_refresh_rotation,
    revoke_session_for_token,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth/cli", tags=["CLI Authentication"])


@router.post("/register", response_model=CliAuthRegisterResponse)
async def cli_register(body: CliAuthRegisterRequest) -> CliAuthRegisterResponse:
    """Start a CLI login session (called by the CLI before opening the browser)."""
    try:
        data = await register_cli_session(
            code_challenge=body.code_challenge,
            code_challenge_method=body.code_challenge_method,
            state=body.state,
            redirect_uri=body.redirect_uri,
            device_name=body.device_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )
    return CliAuthRegisterResponse(**data)


@router.post("/approve", response_model=CliAuthApproveResponse)
async def cli_approve(
    body: CliAuthApproveRequest,
    current_user: User = Depends(get_current_user),
) -> CliAuthApproveResponse:
    """Complete browser authorization after the user signs in on the web app."""
    try:
        redirect_uri = await approve_cli_session(
            session_id=body.session_id,
            state=body.state,
            user_id=str(current_user.id),
        )
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or expired")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )
    return CliAuthApproveResponse(redirect_uri=redirect_uri)


@router.post("/token", response_model=CliAuthTokenResponse)
async def cli_token(
    body: CliAuthTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CliAuthTokenResponse:
    """Exchange authorization code + PKCE verifier for CLI tokens."""
    code_payload = await consume_code(body.code)
    if not code_payload or code_payload.get("used"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code")
    if code_payload.get("session_id") != body.session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session mismatch")
    if not verify_pkce(body.code_verifier, code_payload["code_challenge"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PKCE verifier")

    session = None
    from app.services import cli_auth_service

    session = await cli_auth_service._load_session(body.session_id)
    if not session or not secrets_compare(session.get("state"), body.state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state")
    if session.get("status") != "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session not approved")
    if str(session.get("user_id")) != str(code_payload.get("user_id")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session user mismatch")
    if code_payload.get("redirect_uri") != session.get("redirect_uri"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Redirect URI mismatch")

    try:
        user_uuid = UUID(code_payload["user_id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user") from exc

    user = await db.get(User, user_uuid)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    device = session.get("device_name") or "DevArchAI CLI"
    user_session, raw_refresh = await create_refresh_session(
        db,
        user,
        request,
        token_family=str(uuid4()),
        device=device,
        browser="CLI",
        os_name="CLI",
    )
    user_session.device_name = device[:255]
    await db.commit()

    claims = _enrich_jwt_claims(user)
    access = create_access_token(data=claims)
    expires_in = int(settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60
    email = user_to_response(user).email

    logger.info("cli_auth_token_issued", user_id=str(user.id)[:8], session_id=str(user_session.id)[:8])
    return CliAuthTokenResponse(
        access_token=access,
        refresh_token=raw_refresh,
        expires_in=expires_in,
        session_id=str(user_session.id),
        email=email,
    )


def secrets_compare(a: str | None, b: str) -> bool:
    import secrets as sec

    return sec.compare_digest(str(a or ""), b)


@router.post("/refresh", response_model=CliAuthTokenResponse)
async def cli_refresh(
    body: CliAuthRefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CliAuthTokenResponse:
    """Rotate CLI refresh token and issue a new access token."""
    user, new_raw, session = await perform_refresh_rotation(db, request, body.refresh_token)
    claims = _enrich_jwt_claims(user)
    access = create_access_token(data=claims)
    expires_in = int(settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60
    email = user_to_response(user).email
    return CliAuthTokenResponse(
        access_token=access,
        refresh_token=new_raw,
        expires_in=expires_in,
        session_id=str(session.id),
        email=email,
    )


@router.post("/revoke")
async def cli_revoke(
    body: CliAuthRevokeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke a single CLI refresh session without affecting web login cookies."""
    token_hash = hash_token(body.refresh_token)
    from sqlalchemy import select

    from app.models.settings import UserSession

    result = await db.execute(
        select(UserSession).where(UserSession.refresh_token_hash == token_hash)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    await revoke_session_for_token(db, session.user_id, body.refresh_token)
    await db.commit()
    logger.info("cli_session_revoked", session_id=str(session.id)[:8])
    return {"message": "CLI session revoked", "success": True}