"""Tests for Settings-page ``sk-`` API key creation and authentication."""

import asyncio
import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

os.environ["DEVSEC_API_KEY_STORE_FILE"] = str(
    Path(tempfile.gettempdir()) / "devsec-test-api-keys.json"
)

from app.core import api_key_store  # noqa: E402  (env var must be set first)
from app.core.security import get_current_user_from_api_key  # noqa: E402
from app.models.user import User  # noqa: E402


def _make_user(user_id: uuid.UUID, **kwargs) -> User:
    return User(
        id=user_id,
        email_encrypted="encrypted",
        email_hash=f"hash-{user_id}",
        username=f"user-{user_id}",
        hashed_password="hashed",
        **kwargs,
    )


def _fake_db(user: User | None = None):
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: user))
    db.commit = AsyncMock()
    return db


def _run(coro):
    return asyncio.run(coro)


def test_api_key_store_roundtrip():
    user_id = str(uuid.uuid4())
    entry = api_key_store.create_api_key_entry(user_id, "ci")

    assert entry["full_key"].startswith("sk-")
    assert entry["masked_key"] == f"sk-****{entry['full_key'][-4:]}"
    assert api_key_store.lookup_user_id_by_key(entry["full_key"]) == user_id
    assert api_key_store.lookup_user_id_by_key("sk-bogus") is None
    assert api_key_store.user_has_api_keys(user_id) is True

    listed = api_key_store.list_api_keys(user_id)
    assert len(listed) == 1
    assert "full_key" not in listed[0]
    assert listed[0]["masked_key"].startswith("sk-****")

    assert api_key_store.revoke_key_by_value(user_id, entry["full_key"]) is True
    assert api_key_store.lookup_user_id_by_key(entry["full_key"]) is None
    assert api_key_store.revoke_key_by_value(user_id, entry["full_key"]) is False
    assert api_key_store.user_has_api_keys(user_id) is False


def test_api_key_store_survives_reload():
    from app.core import api_key_store as store

    user_id = str(uuid.uuid4())
    entry = store.create_api_key_entry(user_id, "persisted")

    store._load()  # simulate a process restart re-reading the file

    assert store.lookup_user_id_by_key(entry["full_key"]) == user_id
    store.remove_all_api_keys(user_id)
    assert store.lookup_user_id_by_key(entry["full_key"]) is None


def test_sk_key_authenticates_user():
    user_id = uuid.uuid4()
    entry = api_key_store.create_api_key_entry(str(user_id), "ci")
    user = _make_user(user_id)

    result = _run(get_current_user_from_api_key(entry["full_key"], _fake_db(user)))

    assert result is user


def test_unknown_sk_key_rejected():
    user_id = uuid.uuid4()
    user = _make_user(user_id)

    result = _run(get_current_user_from_api_key("sk-does-not-exist", _fake_db(user)))

    assert result is None


def test_legacy_dk_key_path():
    user_id = uuid.uuid4()
    user = _make_user(user_id, api_key="dk_abcd_supersecret", api_key_prefix="dk_abcd")

    ok = _run(get_current_user_from_api_key("dk_abcd_supersecret", _fake_db(user)))
    assert ok is user

    bad = _run(get_current_user_from_api_key("dk_abcd_wrong", _fake_db(user)))
    assert bad is None
