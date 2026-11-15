"""PKCE-based CLI authorization sessions (Redis-backed)."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse, urlencode

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

_CLI_SESSION_PREFIX = "cli_auth:session:"
_CLI_CODE_PREFIX = "cli_auth:code:"


def _b64url_no_pad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def verify_pkce(verifier: str, challenge: str) -> bool:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    computed = _b64url_no_pad(digest)
    return secrets.compare_digest(computed, challenge)


def _validate_redirect_uri(redirect_uri: str) -> None:
    parsed = urlparse(redirect_uri.strip())
    if parsed.scheme != "http":
        raise ValueError("redirect_uri must use http scheme for loopback")
    host = (parsed.hostname or "").lower()
    if host not in {"127.0.0.1", "localhost", "[::1]"}:
        raise ValueError("redirect_uri must target loopback")
    if not parsed.port:
        raise ValueError("redirect_uri must include an explicit port")


async def _redis():
    from app.cache.redis_cache import get_cache

    cache = await get_cache()
    if not cache._connected or cache._redis is None:
        raise ConnectionError("Redis unavailable")
    return cache._redis


async def register_cli_session(
    *,
    code_challenge: str,
    code_challenge_method: str,
    state: str,
    redirect_uri: str,
    device_name: str | None,
) -> dict[str, Any]:
    if code_challenge_method != "S256":
        raise ValueError("Only S256 is supported")
    _validate_redirect_uri(redirect_uri)

    session_id = secrets.token_urlsafe(24)
    payload = {
        "code_challenge": code_challenge,
        "state": state,
        "redirect_uri": redirect_uri,
        "device_name": (device_name or "").strip() or None,
        "status": "pending",
        "created_at": datetime.now(UTC).isoformat(),
    }
    redis = await _redis()
    ttl = int(settings.CLI_AUTH_SESSION_TTL_SECONDS)
    await redis.setex(f"{_CLI_SESSION_PREFIX}{session_id}", ttl, json.dumps(payload))

    frontend = settings.FRONTEND_URL.rstrip("/")
    query = urlencode({"session_id": session_id, "state": state})
    authorize_url = f"{frontend}/cli/authorize?{query}"
    return {
        "session_id": session_id,
        "authorize_url": authorize_url,
        "expires_in": ttl,
    }


async def _load_session(session_id: str) -> dict[str, Any] | None:
    redis = await _redis()
    raw = await redis.get(f"{_CLI_SESSION_PREFIX}{session_id}")
    if not raw:
        return None
    data = json.loads(raw)
    return data if isinstance(data, dict) else None


async def approve_cli_session(
    *,
    session_id: str,
    state: str,
    user_id: str,
) -> str:
    redis = await _redis()
    once_key = f"{_CLI_SESSION_PREFIX}{session_id}:issued"
    session = await _load_session(session_id)
    if not session or session.get("status") != "pending":
        raise LookupError("session_not_found")
    if not secrets.compare_digest(str(session.get("state", "")), state):
        raise ValueError("invalid_state")

    # Prevent duplicate approval / parallel double-code issuance for one session.
    issued = await redis.set(once_key, user_id, nx=True, ex=int(settings.CLI_AUTH_CODE_TTL_SECONDS))
    if not issued:
        raise LookupError("session_not_found")

    code = secrets.token_urlsafe(32)
    code_payload = {
        "session_id": session_id,
        "user_id": user_id,
        "code_challenge": session["code_challenge"],
        "redirect_uri": session["redirect_uri"],
        "used": False,
    }
    code_ttl = int(settings.CLI_AUTH_CODE_TTL_SECONDS)
    await redis.setex(f"{_CLI_CODE_PREFIX}{code}", code_ttl, json.dumps(code_payload))

    session["status"] = "approved"
    session["user_id"] = user_id
    ttl = await redis.ttl(f"{_CLI_SESSION_PREFIX}{session_id}")
    if ttl > 0:
        await redis.setex(f"{_CLI_SESSION_PREFIX}{session_id}", ttl, json.dumps(session))

    redirect_base = session["redirect_uri"]
    sep = "&" if "?" in redirect_base else "?"
    redirect_uri = f"{redirect_base}{sep}{urlencode({'code': code, 'state': state})}"
    return redirect_uri


async def load_code_payload(code: str) -> dict[str, Any] | None:
    redis = await _redis()
    raw = await redis.get(f"{_CLI_CODE_PREFIX}{code}")
    if not raw:
        return None
    data = json.loads(raw)
    return data if isinstance(data, dict) else None


async def consume_code(code: str) -> dict[str, Any] | None:
    redis = await _redis()
    key = f"{_CLI_CODE_PREFIX}{code}"
    raw = await redis.getdel(key)
    if not raw:
        return None
    data = json.loads(raw)
    return data if isinstance(data, dict) else None


async def mark_code_used(code: str) -> None:
    redis = await _redis()
    await redis.delete(f"{_CLI_CODE_PREFIX}{code}")