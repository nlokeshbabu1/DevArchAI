"""Store for user API keys created in the Settings page.

Persisted to a local JSON file so keys survive backend restarts (the in-memory
sessions/preferences stores do not, but keys are irreplaceable credentials).
Swap this for the database-backed store when one exists.
"""

from __future__ import annotations

import json
import os
import secrets
import threading
from datetime import UTC, datetime
from pathlib import Path

_api_keys_store: dict[str, list[dict]] = {}

_lock = threading.Lock()
_STORE_FILE = Path(
    os.environ.get(
        "DEVSEC_API_KEY_STORE_FILE",
        str(Path(__file__).resolve().parents[2] / "data" / "api_keys.json"),
    )
)


def _load() -> None:
    global _api_keys_store
    try:
        data = json.loads(_STORE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    _api_keys_store = data if isinstance(data, dict) else {}


def _save() -> None:
    try:
        _STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _STORE_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(_api_keys_store), encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(_STORE_FILE)
        os.chmod(_STORE_FILE, 0o600)
    except OSError:
        pass  # best effort - the key stays valid for this process either way


def create_api_key_entry(user_id: str, name: str = "") -> dict:
    """Create a new ``sk-`` API key entry and return the full key once."""
    with _lock:
        key_id = f"key_{secrets.token_urlsafe(12)}"
        raw_key = f"sk-{secrets.token_urlsafe(32)}"
        now = datetime.now(UTC).isoformat()
        entry = {
            "id": key_id,
            "name": name,
            "masked_key": f"sk-****{raw_key[-4:]}",
            "full_key": raw_key,
            "created_at": now,
        }
        if user_id not in _api_keys_store:
            _api_keys_store[user_id] = []
        _api_keys_store[user_id].insert(0, entry)
        _save()
        return entry


def list_api_keys(user_id: str) -> list[dict]:
    """Return key metadata without the raw key material."""
    return [
        {
            "id": k["id"],
            "name": k.get("name", ""),
            "masked_key": k.get("masked_key", f"sk-****{k['id'][-4:]}"),
            "created_at": k.get("created_at"),
        }
        for k in _api_keys_store.get(user_id, [])
    ]


def revoke_api_key(user_id: str, key_id: str) -> bool:
    """Revoke a key by id; returns True when a key was removed."""
    with _lock:
        keys = _api_keys_store.get(user_id, [])
        before = len(keys)
        _api_keys_store[user_id] = [k for k in keys if k["id"] != key_id]
        removed = len(_api_keys_store[user_id]) != before
        if removed:
            _save()
        return removed


def revoke_key_by_value(user_id: str, raw_key: str) -> bool:
    """Revoke a key by its raw value; returns True when a key was removed."""
    with _lock:
        keys = _api_keys_store.get(user_id, [])
        before = len(keys)
        _api_keys_store[user_id] = [k for k in keys if k.get("full_key") != raw_key]
        removed = len(_api_keys_store[user_id]) != before
        if removed:
            _save()
        return removed


def remove_all_api_keys(user_id: str) -> None:
    with _lock:
        if user_id in _api_keys_store:
            del _api_keys_store[user_id]
            _save()


def lookup_user_id_by_key(raw_key: str) -> str | None:
    """Return the user id that owns ``raw_key``, or None."""
    for uid, keys in _api_keys_store.items():
        for k in keys:
            if k.get("full_key") == raw_key:
                return uid
    return None


def user_has_api_keys(user_id: str) -> bool:
    """True when the user has at least one active ``sk-`` key."""
    return bool(_api_keys_store.get(user_id))


_load()
