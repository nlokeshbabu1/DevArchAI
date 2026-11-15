"""Refresh-token HttpOnly cookie helpers (consistent set/delete attributes)."""

from __future__ import annotations

from fastapi import Request, Response

from app.config import settings


def refresh_cookie_name() -> str:
    """Cookie name; __Host- prefix when Secure (production pattern)."""
    if settings.COOKIE_USE_HOST_PREFIX and settings.COOKIE_SECURE:
        return "__Host-devarchai_refresh"
    return settings.REFRESH_COOKIE_NAME


def legacy_refresh_cookie_names() -> tuple[str, ...]:
    """Previous cookie names accepted during migration."""
    return ("refresh_token", "devarchai_refresh")


def read_refresh_token_from_request(request: Request) -> str | None:
    """Read refresh token from cookie (current name, then legacy names)."""
    name = refresh_cookie_name()
    token = request.cookies.get(name)
    if token:
        return token
    for legacy in legacy_refresh_cookie_names():
        if legacy == name:
            continue
        token = request.cookies.get(legacy)
        if token:
            return token
    return None


def refresh_cookie_params() -> dict:
    """Keyword arguments shared by set_cookie and delete_cookie for refresh tokens."""
    use_host = settings.COOKIE_USE_HOST_PREFIX and settings.COOKIE_SECURE
    path = "/" if use_host else settings.COOKIE_PATH
    params: dict = {
        "key": refresh_cookie_name(),
        "path": path,
        "secure": settings.COOKIE_SECURE,
        "httponly": True,
        "samesite": settings.COOKIE_SAMESITE,
    }
    if not use_host and settings.COOKIE_DOMAIN:
        params["domain"] = settings.COOKIE_DOMAIN
    return params


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Set the HttpOnly refresh token cookie."""
    params = refresh_cookie_params()
    response.set_cookie(
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        **params,
    )


def clear_refresh_cookie(response: Response) -> None:
    """Delete refresh cookies (current + legacy names) with matching attributes."""
    params = refresh_cookie_params()
    response.delete_cookie(**params)
    use_host = settings.COOKIE_USE_HOST_PREFIX and settings.COOKIE_SECURE
    path = "/" if use_host else settings.COOKIE_PATH
    for legacy in legacy_refresh_cookie_names():
        if legacy == params["key"]:
            continue
        legacy_params = {
            "key": legacy,
            "path": path,
            "secure": settings.COOKIE_SECURE,
            "httponly": True,
            "samesite": settings.COOKIE_SAMESITE,
        }
        if not use_host and settings.COOKIE_DOMAIN:
            legacy_params["domain"] = settings.COOKIE_DOMAIN
        response.delete_cookie(**legacy_params)
    if settings.COOKIE_PATH != path:
        response.delete_cookie(
            key="refresh_token",
            path=settings.COOKIE_PATH,
            secure=settings.COOKIE_SECURE,
            httponly=True,
            samesite=settings.COOKIE_SAMESITE,
        )
