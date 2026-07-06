"""Settings routes for user profile, preferences, sessions, API keys, and account management."""

import secrets
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    decrypt_user_email,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/settings", tags=["Settings"])

# ── In-memory fallback stores (used when DB tables don't exist) ──
_preferences_store: dict[str, dict] = {}
_sessions_store: dict[str, list[dict]] = {}
_api_keys_store: dict[str, list[dict]] = {}


# def _get_email(user: User) -> str:
#     try:
#         return decrypt_user_email(user.email_encrypted)
#     except Exception:
#         return user.email_encrypted if user.email_encrypted else "email@example.com"

def _get_email(user: User) -> str:
    if not user.email_encrypted:
        return "Email unavailable"

    # If the raw stored value already looks like an email, use it directly
    # (handles legacy plaintext storage without risking encrypted blob exposure)
    if "@" in user.email_encrypted:
        return user.email_encrypted

    try:
        decrypted_email = decrypt_user_email(user.email_encrypted)
        if "@" in decrypted_email:
            return decrypted_email
    except Exception as e:
        logger.warning("Email decrypt failed for user_id=%s: %s", user.id, e)

    # Cannot decrypt – show user-based placeholder instead of "Email unavailable"
    return f"{user.username}@email.local"


def _profile_dict(user: User, org_name: str | None = None) -> dict:
    logger.info("Fetching settings profile", user_id=str(user.id))
    return {
        "id": str(user.id),
        "email": _get_email(user),
        "username": user.username,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "organization": org_name or "",
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "is_verified": user.is_verified,
        "plan": user.subscription_plan if hasattr(user, "subscription_plan") else "free",
        "created_at": (user.created_at.isoformat() if user.created_at else None),
        "last_login_at": (user.last_login_at.isoformat() if user.last_login_at else None),
        "provider": (
            "email+github" if (user.github_id and user.hashed_password)
            else "email+gitlab" if (user.gitlab_id and user.hashed_password)
            else "github" if user.github_id
            else "gitlab" if user.gitlab_id
            else "email"
        ),
        "has_password": bool(user.hashed_password),
    }


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_name = ""
    if current_user.current_org_id:
        try:
            result = await db.execute(
                select(Organization).where(Organization.id == current_user.current_org_id)
            )
            org = result.scalar_one_or_none()
            if org:
                org_name = org.name or ""
        except Exception:
            logger.warning("Could not fetch organization", exc_info=True)
    return _profile_dict(current_user, org_name)


@router.put("/profile")
async def update_profile(
    body: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    changed = False
    if "full_name" in body and body["full_name"] is not None:
        current_user.full_name = str(body["full_name"])
        changed = True
    if "username" in body and body["username"] is not None:
        new_username = str(body["username"]).strip()
        if new_username != current_user.username:
            result = await db.execute(select(User).where(User.username == new_username))
            if result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Username already taken")
            current_user.username = new_username
            changed = True
    if changed:
        await db.commit()
        await db.refresh(current_user)

    org_name = ""
    if current_user.current_org_id:
        try:
            result = await db.execute(
                select(Organization).where(Organization.id == current_user.current_org_id)
            )
            org = result.scalar_one_or_none()
            if org:
                org_name = org.name or ""
        except Exception:
            pass
    return _profile_dict(current_user, org_name)


@router.put("/password")
async def change_password(
    body: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current = body.get("current_password", "")
    new_pw = body.get("new_password", "")
    if not current:
        raise HTTPException(status_code=400, detail="Current password is required")
    if not new_pw or len(new_pw) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    if not verify_password(current, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = get_password_hash(new_pw)
    await db.commit()
    return {"message": "Password updated successfully", "success": True}


@router.get("/preferences")
async def get_preferences(current_user: User = Depends(get_current_user)):
    uid = str(current_user.id)
    logger.info("Fetching preferences", user_id=uid)
    defaults = {
        "email_notifications": True,
        "security_alerts": True,
        "weekly_reports": False,
        "product_updates": False,
        "scan_completion_alerts": True,
        "theme": "dark",
    }
    stored = _preferences_store.get(uid, {})
    return {**defaults, **stored}


@router.put("/preferences")
async def update_preferences(
    body: dict = Body(...),
    current_user: User = Depends(get_current_user),
):
    uid = str(current_user.id)
    logger.info("Updating preferences", user_id=uid, preferences=body)
    _preferences_store[uid] = body
    return body


@router.get("/sessions")
async def get_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get active sessions for the current user (from DB)."""
    from app.models.settings import UserSession
    try:
        result = await db.execute(
            select(UserSession).where(
                UserSession.user_id == current_user.id,
                UserSession.revoked.is_(False),
            ).order_by(UserSession.last_active_at.desc())
        )
        db_sessions = result.scalars().all()
        return [
            {
                "id": str(s.id),
                "device": s.device_name or s.browser or "Unknown",
                "ip_address": s.ip_address,
                "last_active": s.last_active_at.isoformat() if s.last_active_at else None,
                "current": s.is_current,
            }
            for s in db_sessions
        ]
    except Exception:
        pass
    # Fallback to in-memory store
    uid = str(current_user.id)
    existing = _sessions_store.get(uid, [])
    now = datetime.now(UTC).isoformat()
    current_session = {
        "id": f"sess_{secrets.token_urlsafe(8)}",
        "device": "Chrome on Linux",
        "ip_address": "127.0.0.1",
        "last_active": now,
        "current": True,
    }
    all_sessions = [current_session] + existing
    seen = set()
    deduped = []
    for s in all_sessions:
        if s["id"] not in seen:
            seen.add(s["id"])
            deduped.append(s)
    return deduped


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a session by ID."""
    from uuid import UUID as UUIDType

    from app.models.settings import UserSession
    try:
        session_uuid = UUIDType(session_id)
        result = await db.execute(
            select(UserSession).where(
                UserSession.id == session_uuid,
                UserSession.user_id == current_user.id,
            )
        )
        session = result.scalar_one_or_none()
        if session:
            session.revoked = True
            session.is_current = False
            await db.commit()
            return {"message": "Session revoked successfully", "success": True}
    except Exception:
        pass
    if session_id.startswith("sess_"):
        for uid, sessions in _sessions_store.items():
            _sessions_store[uid] = [s for s in sessions if s["id"] != session_id]
        return {"message": "Session revoked successfully", "success": True}
    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/api-keys")
async def list_api_keys(current_user: User = Depends(get_current_user)):
    uid = str(current_user.id)
    logger.info("Fetching API keys", user_id=uid)
    keys = []
    existing = _api_keys_store.get(uid, [])
    for k in existing:
        keys.append({
            "id": k["id"],
            "name": k.get("name", ""),
            "masked_key": k.get("masked_key", f"sk-****{k['id'][-4:]}"),
            "created_at": k.get("created_at"),
        })
    if current_user.api_key_prefix and current_user.api_key:
        keys.append({
            "id": "legacy_key",
            "name": "Legacy API Key",
            "masked_key": f"{current_user.api_key_prefix}****",
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        })
    return keys


@router.post("/api-keys")
async def create_api_key(
    body: dict = Body({}),
    current_user: User = Depends(get_current_user),
):
    uid = str(current_user.id)
    key_id = f"key_{secrets.token_urlsafe(12)}"
    raw_key = f"sk-{secrets.token_urlsafe(32)}"
    name = body.get("name", "")
    now = datetime.now(UTC).isoformat()
    entry = {
        "id": key_id,
        "name": name,
        "masked_key": f"sk-****{raw_key[-4:]}",
        "full_key": raw_key,
        "created_at": now,
    }
    if uid not in _api_keys_store:
        _api_keys_store[uid] = []
    _api_keys_store[uid].insert(0, {
        "id": key_id,
        "name": name,
        "masked_key": entry["masked_key"],
        "created_at": now,
    })
    return entry


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
):
    uid = str(current_user.id)
    if uid in _api_keys_store:
        _api_keys_store[uid] = [k for k in _api_keys_store[uid] if k["id"] != key_id]
    return {"message": "API key revoked successfully", "success": True}


@router.delete("/account")
async def delete_account(
    body: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pw = body.get("password", "")
    if not pw:
        raise HTTPException(status_code=400, detail="Password is required")
    if not verify_password(pw, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Password is incorrect")
    uid = str(current_user.id)
    _preferences_store.pop(uid, None)
    _sessions_store.pop(uid, None)
    _api_keys_store.pop(uid, None)
    await db.delete(current_user)
    await db.commit()
    return {"message": "Account deleted successfully", "success": True}
