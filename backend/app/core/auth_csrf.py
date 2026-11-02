"""CSRF / Origin checks for cookie-based auth endpoints."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.config import settings


def verify_refresh_origin(request: Request) -> None:
    """Reject cross-site refresh attempts when Origin is present."""
    origin = request.headers.get("origin")
    if not origin:
        return
    allowed = set(settings.CORS_ORIGINS or [])
    if origin not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origin not allowed",
        )
