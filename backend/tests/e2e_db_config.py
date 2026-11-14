"""Dedicated PostgreSQL target for browser E2E (never dev 5432 or production)."""

from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

E2E_DB_NAME = "devarchai_e2e"
ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost"})
ALLOWED_PORTS = frozenset({5433})

_DEFAULT_SYNC = (
    f"postgresql://{os.environ.get('E2E_POSTGRES_USER', 'postgres')}:"
    f"{os.environ.get('E2E_POSTGRES_PASSWORD', 'postgres')}"
    f"@{os.environ.get('E2E_POSTGRES_HOST', '127.0.0.1')}:"
    f"{os.environ.get('E2E_POSTGRES_PORT', '5433')}/{E2E_DB_NAME}"
)


def get_e2e_sync_database_url() -> str:
    raw = os.environ.get("E2E_DATABASE_URL", os.environ.get("DATABASE_URL", _DEFAULT_SYNC))
    if raw.startswith("postgresql+asyncpg://"):
        raw = raw.replace("postgresql+asyncpg://", "postgresql://", 1)
    return raw


def get_e2e_async_database_url() -> str:
    sync = get_e2e_sync_database_url()
    return sync.replace("postgresql://", "postgresql+asyncpg://", 1)


def assert_e2e_database_approved(url: str | None = None) -> str:
    """Fail fast if E2E would touch an unapproved database."""
    sync = url or get_e2e_sync_database_url()
    parsed = urlparse(sync)
    host = (parsed.hostname or "").lower()
    port = parsed.port or 5432
    db = (parsed.path or "").lstrip("/")

    if host not in ALLOWED_HOSTS:
        print(f"E2E REFUSED: host {host!r} not in {sorted(ALLOWED_HOSTS)}", file=sys.stderr)
        sys.exit(1)
    if port not in ALLOWED_PORTS:
        print(f"E2E REFUSED: port {port} not in {sorted(ALLOWED_PORTS)} (dev uses 5432)", file=sys.stderr)
        sys.exit(1)
    if db != E2E_DB_NAME:
        print(f"E2E REFUSED: database {db!r} must be {E2E_DB_NAME!r}", file=sys.stderr)
        sys.exit(1)
    return sync


def apply_e2e_database_env() -> str:
    sync = assert_e2e_database_approved()
    async_url = get_e2e_async_database_url()
    os.environ["E2E_DATABASE_URL"] = sync
    os.environ["DATABASE_URL"] = async_url
    os.environ.setdefault("TESTING", "true")
    return sync