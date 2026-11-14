"""WebSocket authentication: first-message credentials, origin checks, ownership."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from fastapi import WebSocket
from sqlalchemy import select

from app.config import settings
from app.core.security import decode_token

logger = structlog.get_logger(__name__)

WS_AUTH_TIMEOUT_SECONDS = 10.0
WS_MAX_AUTH_MESSAGE_BYTES = 4096

# Close codes (application-specific band)
WS_CLOSE_AUTH_REQUIRED = 4001
WS_CLOSE_ACCESS_DENIED = 4003
WS_CLOSE_MESSAGE_TOO_LARGE = 1009


@dataclass
class WebSocketCredentials:
    access_token: str | None = None
    api_key: str | None = None
    session_token: str | None = None


def is_websocket_origin_allowed(origin: str | None) -> bool:
    """Allow missing Origin (CLI/non-browser); browsers must match CORS allowlist."""
    if not origin:
        return True
    return origin in settings.CORS_ORIGINS


def _reject_query_string_credentials(websocket: WebSocket) -> bool:
    """Return True if legacy query-string credentials were present (rejected)."""
    legacy_keys = ("token", "api_key", "access_token", "session_token")
    if any(websocket.query_params.get(key) for key in legacy_keys):
        logger.warning("ws_auth_query_params_rejected", path=websocket.url.path)
        return True
    return False


def _parse_auth_message(raw: str) -> WebSocketCredentials | None:
    if len(raw) > WS_MAX_AUTH_MESSAGE_BYTES:
        return None
    try:
        message = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if message.get("type") != "auth":
        return None
    payload = message.get("data") if isinstance(message.get("data"), dict) else message
    return WebSocketCredentials(
        access_token=payload.get("access_token") or payload.get("token"),
        api_key=payload.get("api_key"),
        session_token=payload.get("session_token"),
    )


async def _access_token_valid(access_token: str) -> dict[str, Any] | None:
    payload = decode_token(access_token)
    if not payload or payload.get("type") != "access":
        return None
    jti = payload.get("jti")
    if jti:
        from app.services.token_blacklist import BlacklistRedisError, is_blacklisted

        try:
            if await is_blacklisted(jti):
                return None
        except BlacklistRedisError:
            logger.error("ws_auth_blacklist_unavailable", jti=jti[:8])
            return None
    return payload


async def receive_websocket_credentials(websocket: WebSocket) -> WebSocketCredentials | None:
    """
    Accept the socket, enforce Origin policy, and read a first-message auth payload.

    Rejects credentials in the URL query string.
    """
    origin = websocket.headers.get("origin")
    if not is_websocket_origin_allowed(origin):
        await websocket.close(code=WS_CLOSE_ACCESS_DENIED, reason="Origin not allowed")
        return None

    if _reject_query_string_credentials(websocket):
        await websocket.close(code=WS_CLOSE_AUTH_REQUIRED, reason="Authentication required")
        return None

    await websocket.accept()

    try:
        raw = await asyncio.wait_for(
            websocket.receive_text(),
            timeout=WS_AUTH_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        await websocket.close(code=WS_CLOSE_AUTH_REQUIRED, reason="Authentication timeout")
        return None

    creds = _parse_auth_message(raw)
    if creds is None:
        await websocket.close(code=WS_CLOSE_AUTH_REQUIRED, reason="Authentication required")
        return None
    if not any((creds.access_token, creds.api_key, creds.session_token)):
        await websocket.close(code=WS_CLOSE_AUTH_REQUIRED, reason="Authentication required")
        return None
    return creds


def _user_id_from_api_key(api_key: str) -> UUID | None:
    from app.db.session import get_sync_session_factory
    from app.models.user import User

    if api_key.startswith("sk-"):
        from app.core.api_key_store import lookup_user_id_by_key

        uid = lookup_user_id_by_key(api_key)
        if not uid:
            return None
        sync_db = get_sync_session_factory()()
        try:
            result = sync_db.execute(
                select(User).where(User.id == UUID(uid), User.is_active.is_(True))
            )
            user = result.scalar_one_or_none()
            return user.id if user else None
        finally:
            sync_db.close()

    if "_" not in api_key or not api_key.startswith("dk_"):
        return None

    prefix = api_key.rsplit("_", 1)[0]
    sync_db = get_sync_session_factory()()
    try:
        result = sync_db.execute(
            select(User).where(User.api_key_prefix == prefix, User.is_active.is_(True))
        )
        user = result.scalar_one_or_none()
        from app.core.security import verify_user_api_key

        if user and verify_user_api_key(user.api_key, api_key):
            return user.id
    finally:
        sync_db.close()
    return None


async def resolve_user_id_from_credentials(creds: WebSocketCredentials) -> UUID | None:
    """Resolve an authenticated user id from WS credentials (API key or access JWT)."""
    if creds.api_key:
        return _user_id_from_api_key(creds.api_key)

    if creds.access_token:
        payload = await _access_token_valid(creds.access_token)
        if not payload:
            return None
        sub = payload.get("sub")
        if not sub:
            return None
        try:
            return UUID(sub)
        except (ValueError, AttributeError):
            return None

    return None


async def authorize_scan_access(
    websocket: WebSocket,
    scan_id: str,
    creds: WebSocketCredentials,
) -> bool:
    """Verify credentials grant access to the given scan."""
    from app.db.session import get_sync_session_factory
    from app.models.anonymous_scan import AnonymousScan
    from app.models.scan import Scan

    if creds.api_key or creds.access_token:
        user_id = await resolve_user_id_from_credentials(creds)
        if user_id is None:
            await websocket.close(code=WS_CLOSE_AUTH_REQUIRED, reason="Invalid credentials")
            return False
        sync_db = get_sync_session_factory()()
        try:
            try:
                scan_uuid = UUID(scan_id)
            except ValueError:
                await websocket.close(code=WS_CLOSE_AUTH_REQUIRED, reason="Invalid scan identifier")
                return False
            result = sync_db.execute(
                select(Scan).where(Scan.id == scan_uuid, Scan.user_id == user_id)
            )
            if result.scalar_one_or_none() is None:
                await websocket.close(code=WS_CLOSE_ACCESS_DENIED, reason="Access denied")
                return False
        finally:
            sync_db.close()
        return True

    if creds.session_token:
        sync_db = get_sync_session_factory()()
        try:
            result = sync_db.execute(
                select(AnonymousScan).where(
                    AnonymousScan.session_token == creds.session_token,
                    AnonymousScan.linked_scan_id == scan_id,
                )
            )
            anon_scan = result.scalar_one_or_none()
            if not anon_scan:
                await websocket.close(code=WS_CLOSE_ACCESS_DENIED, reason="Access denied")
                return False
            if anon_scan.expires_at and anon_scan.expires_at < datetime.now(UTC):
                await websocket.close(code=WS_CLOSE_ACCESS_DENIED, reason="Session expired")
                return False
        finally:
            sync_db.close()
        return True

    await websocket.close(code=WS_CLOSE_AUTH_REQUIRED, reason="Authentication required")
    return False


async def authorize_cloud_connection_access(
    websocket: WebSocket,
    connection_id: str,
    creds: WebSocketCredentials,
) -> bool:
    """Cloud progress requires a user JWT or API key; guest session tokens are not supported."""
    if creds.session_token and not (creds.access_token or creds.api_key):
        await websocket.close(code=WS_CLOSE_AUTH_REQUIRED, reason="Authentication required")
        return False

    user_id = await resolve_user_id_from_credentials(creds)
    if user_id is None:
        await websocket.close(code=WS_CLOSE_AUTH_REQUIRED, reason="Invalid credentials")
        return False

    from app.db.session import get_sync_session_factory
    from app.models.cloud import CloudConnection

    sync_db = get_sync_session_factory()()
    try:
        try:
            conn_uuid = UUID(connection_id)
        except ValueError:
            await websocket.close(code=WS_CLOSE_AUTH_REQUIRED, reason="Invalid connection identifier")
            return False
        result = sync_db.execute(
            select(CloudConnection).where(
                CloudConnection.id == conn_uuid,
                CloudConnection.user_id == user_id,
            )
        )
        if result.scalar_one_or_none() is None:
            await websocket.close(code=WS_CLOSE_ACCESS_DENIED, reason="Access denied")
            return False
    finally:
        sync_db.close()
    return True


async def authenticate_scan_websocket(websocket: WebSocket, scan_id: str) -> bool:
    creds = await receive_websocket_credentials(websocket)
    if creds is None:
        return False
    return await authorize_scan_access(websocket, scan_id, creds)


async def authenticate_cloud_websocket(websocket: WebSocket, connection_id: str) -> bool:
    creds = await receive_websocket_credentials(websocket)
    if creds is None:
        return False
    return await authorize_cloud_connection_access(websocket, connection_id, creds)
