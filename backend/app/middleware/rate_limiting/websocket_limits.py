"""WebSocket connection rate limits (per user and per IP)."""

from __future__ import annotations

import structlog
from fastapi import WebSocket

from app.config import settings
from app.core.security import decode_token, hash_token
from app.middleware.rate_limiting.client_ip import get_client_ip
from app.middleware.rate_limiting.sliding_window import RateLimitSpec, check_sliding_window, make_redis_key

logger = structlog.get_logger(__name__)

_WS_CLOSE_RATE_LIMITED = 4029


async def enforce_websocket_connection_limits(
    websocket: WebSocket,
    *,
    user_sub: str | None = None,
    api_key: str | None = None,
    session_token: str | None = None,
) -> bool:
    """
    Return True if the connection may proceed.

    Uses hashed session/token material; never logs secrets.
    """
    if not settings.RATE_LIMIT_ENABLED:
        return True

    client_ip = get_client_ip(websocket)
    specs: list[RateLimitSpec] = []

    specs.append(
        RateLimitSpec(
            redis_key=make_redis_key("ws_connect", "ip", client_ip, "/ws/scan/{scan_id}"),
            max_requests=settings.RATE_LIMIT_WS_MAX_CONNECTIONS_IP,
            window_seconds=settings.RATE_LIMIT_WS_CONNECTION_WINDOW,
            category="ws_connect_ip",
            identity_kind="ip",
        )
    )

    identity: str | None = None
    if user_sub:
        identity = str(user_sub)
    elif api_key:
        identity = f"ak:{hash_token(api_key)}"
    elif session_token:
        identity = f"st:{hash_token(session_token)}"

    if identity:
        specs.append(
            RateLimitSpec(
                redis_key=make_redis_key("ws_connect", "user", identity, "/ws/scan/{scan_id}"),
                max_requests=settings.RATE_LIMIT_WS_MAX_CONNECTIONS_USER,
                window_seconds=settings.RATE_LIMIT_WS_CONNECTION_WINDOW,
                category="ws_connect_user",
                identity_kind="user",
            )
        )

    try:
        for spec in specs:
            result = await check_sliding_window(spec)
            if not result.allowed:
                logger.warning(
                    "ws_rate_limit_exceeded",
                    identity_kind=spec.identity_kind,
                    category=spec.category,
                )
                await websocket.close(code=_WS_CLOSE_RATE_LIMITED, reason="Connection rate limit exceeded")
                return False
    except Exception:
        logger.error("ws_rate_limit_redis_failure", category="ws_connect")
        await websocket.close(code=1013, reason="Service temporarily unavailable")
        return False

    return True


def user_sub_from_access_token(access_token: str | None) -> str | None:
    if not access_token:
        return None
    payload = decode_token(access_token)
    if payload and payload.get("type") == "access":
        sub = payload.get("sub")
        return str(sub) if sub else None
    return None