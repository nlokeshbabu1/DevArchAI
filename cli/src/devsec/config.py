"""Local configuration and secure credential storage.

Configuration precedence (highest wins):

1. Environment variables (``DEVSEC_API_URL``, ``DEVSEC_FRONTEND_URL``,
   ``DEVSEC_API_KEY``) - designed for CI/CD and always non-interactive.
2. Local config file (``~/.config/devsec/config.toml``) - non-secret values
   only, managed by ``devsec config``.
3. Built-in defaults.

Secrets (the API token) are stored in the operating system keyring via
:mod:`keyring`. If no keyring backend is available, the token falls back to
a credentials file with owner-only permissions (``0600``) and a loud warning
is emitted. Tokens are never written to the config TOML.
"""

from __future__ import annotations

import json
import os
import sys
import tomllib
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from devsec.utils.errors import ConfigError, UsageError

APP_NAME = "devsec"

DEFAULT_API_URL = "https://backend.devarchai.xyz"
DEFAULT_FRONTEND_URL = "https://www.devarchai.xyz"

ENV_API_URL = "DEVSEC_API_URL"
ENV_FRONTEND_URL = "DEVSEC_FRONTEND_URL"
# The environment variable *name* is not a secret value; S105 is a false positive.
ENV_API_KEY = "DEVSEC_API_KEY"  # noqa: S105
# Legacy name kept for backward compatibility with CI setups written before
# ``DEVSEC_API_KEY``. Precedence: DEVSEC_API_KEY > DEVSEC_API_TOKEN > keyring.
ENV_API_TOKEN = "DEVSEC_API_TOKEN"  # noqa: S105
CLI_SESSION_KEYRING_USER = "cli_session"

# Keys accepted by `devsec config set`.
CONFIG_KEYS: dict[str, str] = {
    "api-url": "api_url",
    "frontend-url": "frontend_url",
}

PRODUCTION_API_URL = DEFAULT_API_URL
PRODUCTION_FRONTEND_URL = DEFAULT_FRONTEND_URL


def api_url_misconfiguration_hint(url: str) -> str | None:
    """Return a hint when ``api-url`` looks like the frontend app, not the backend API."""
    parsed = urlparse(url.strip().rstrip("/"))
    host = (parsed.hostname or "").lower()
    port = parsed.port

    if port == 5174:
        return (
            f"{url} looks like the frontend dev server (port 5174), not the backend API. "
            f"Run: devsec config set api-url {PRODUCTION_API_URL} "
            f"(or http://localhost:8000 for local backend)."
        )
    if host in {"www.devarchai.xyz", "devarchai.xyz"}:
        return (
            f"{url} is the web app URL, not the API. "
            f"Run: devsec config set api-url {PRODUCTION_API_URL}"
        )
    return None


# Non-secret keys shown by `devsec config list`.
_NON_SECRET_KEYS = ("api_url", "frontend_url")

# Persisted (non-secret) key holding the currently selected project ID. It is
# not a user-facing `config set` key and never appears in `config list`.
SELECTED_PROJECT_KEY = "selected_project"

# Files that are always excluded from scanning regardless of configuration
# (see devsec.utils.filesystem for the full ignore rules).


def _config_dir() -> Path:
    """Return the platform-appropriate config directory."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / APP_NAME
    return Path.home() / ".config" / APP_NAME


def _default_config_file() -> Path:
    return _config_dir() / "config.toml"


def _default_credentials_file() -> Path:
    return _config_dir() / "credentials.json"


class SecretStore:
    """Secure token storage with a keyring-first strategy.

    ``keyring`` is attempted first; on failure (headless containers, no
    backend, permissions) the token is stored in a credentials file with
    ``0600`` permissions. The caller is warned once via :meth:`warning`.
    """

    KEYRING_SERVICE = "devsec"

    def __init__(self, config_file: Path | None = None) -> None:
        self._credentials_file = (
            config_file.parent / "credentials.json"
            if config_file is not None
            else _default_credentials_file()
        )
        self._keyring_backend: Any = None
        self._warned_fallback = False

    @property
    def using_fallback(self) -> bool:
        """True when tokens are stored in the credentials file, not a keyring."""
        return self._keyring() is None

    def _keyring(self) -> Any:
        """Return the keyring backend, or None if unavailable."""
        if self._keyring_backend is not None:
            return self._keyring_backend
        try:
            import keyring

            backend = keyring.get_keyring()
            if getattr(backend, "keyring", None) == "fail":
                return None
            # Verify the backend actually works before trusting it.
            backend.set_password(self.KEYRING_SERVICE, "_probe", "_probe")
            backend.delete_password(self.KEYRING_SERVICE, "_probe")
            self._keyring_backend = backend
            return backend
            # Any keyring backend failure degrades gracefully to the file
            # fallback below; nothing to recover here.
        except Exception:
            self._keyring_backend = None
            return None

    def _fallback_warning(self) -> str:
        if self._warned_fallback:
            return ""
        self._warned_fallback = True
        return (
            "No OS keyring available - storing token in "
            f"{self._credentials_file} with 0600 permissions. "
            "Install a keyring backend (e.g. libsecret) for stronger storage."
        )

    def set_token(self, token: str, username: str = "default") -> None:
        """Store a token securely, preferring the OS keyring."""
        backend = self._keyring()
        if backend is not None:
            backend.set_password(self.KEYRING_SERVICE, username, token)
            return
        self._credentials_file.parent.mkdir(parents=True, exist_ok=True)
        data = self._read_credentials()
        data[username] = token
        self._credentials_file.write_text(json.dumps(data), encoding="utf-8")
        try:
            self._credentials_file.chmod(0o600)
        except OSError:
            pass
        warning = self._fallback_warning()
        if warning:
            print(warning, file=sys.stderr)

    def get_token(self, username: str = "default") -> str | None:
        """Return the stored token for a username, or None."""
        backend = self._keyring()
        if backend is not None:
            try:
                value = backend.get_password(self.KEYRING_SERVICE, username)
                return value or None
            except Exception:
                return None
        return self._read_credentials().get(username)

    def delete_token(self, username: str = "default") -> None:
        """Remove a stored token, ignoring failures."""
        backend = self._keyring()
        if backend is not None:
            try:
                backend.delete_password(self.KEYRING_SERVICE, username)
            except Exception:  # noqa: S110 - token removal must never fail logout
                pass
            return
        data = self._read_credentials()
        data.pop(username, None)
        if data:
            self._credentials_file.write_text(json.dumps(data), encoding="utf-8")
        elif self._credentials_file.exists():
            self._credentials_file.unlink()

    def _read_credentials(self) -> dict[str, str]:
        if not self._credentials_file.exists():
            return {}
        try:
            data = json.loads(self._credentials_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except (json.JSONDecodeError, OSError):
            pass
        return {}


class Config:
    """Resolved configuration with env-var override semantics."""

    def __init__(
        self,
        config_file: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self._config_file = config_file or _default_config_file()
        self._env = os.environ if env is None else env
        self.secrets = SecretStore(config_file=self._config_file)

    # ------------------------------------------------------------------
    # Config file persistence
    # ------------------------------------------------------------------

    @property
    def config_file(self) -> Path:
        return self._config_file

    def _load_file(self) -> dict[str, Any]:
        if not self._config_file.exists():
            return {}
        try:
            with self._config_file.open("rb") as fh:
                data = tomllib.load(fh)
        except (tomllib.TOMLDecodeError, OSError) as exc:
            raise ConfigError(f"Invalid config file at {self._config_file}: {exc}") from exc
        if not isinstance(data, dict):
            return {}
        return data

    def _save_file(self, data: dict[str, Any]) -> None:
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        body = "\n".join(
            f'{key} = "{value}"' for key, value in sorted(data.items()) if isinstance(value, str)
        )
        self._config_file.write_text(body + "\n", encoding="utf-8")

    def set(self, key: str, value: str) -> None:
        """Set a non-secret config value."""
        mapped = CONFIG_KEYS.get(key)
        if mapped is None:
            raise UsageError(
                f"Unknown config key: {key}",
                hint=f"Valid keys: {', '.join(sorted(CONFIG_KEYS))}",
            )
        if not value.strip():
            raise UsageError(f"Value for '{key}' cannot be empty")
        if key == "api-url":
            hint = api_url_misconfiguration_hint(value.strip())
            if hint:
                raise UsageError(
                    "Invalid api-url — this is not the backend API.",
                    hint=hint,
                )
        data = self._load_file()
        data[mapped] = value.strip()
        self._save_file(data)

    def unset(self, key: str) -> None:
        """Remove a non-secret config value."""
        mapped = CONFIG_KEYS.get(key)
        if mapped is None:
            raise UsageError(
                f"Unknown config key: {key}",
                hint=f"Valid keys: {', '.join(sorted(CONFIG_KEYS))}",
            )
        data = self._load_file()
        if mapped in data:
            del data[mapped]
            self._save_file(data)

    def file_values(self) -> dict[str, str]:
        """Return non-secret values persisted in the config file."""
        data = self._load_file()
        return {k: str(v) for k, v in data.items() if k in _NON_SECRET_KEYS}

    @property
    def selected_project(self) -> str | None:
        """The locally selected project (repository) ID, if any."""
        data = self._load_file()
        value = data.get(SELECTED_PROJECT_KEY)
        return str(value) if value else None

    def set_selected_project(self, project_id: str) -> None:
        """Persist the selected project (repository) ID locally."""
        if not project_id.strip():
            raise UsageError("Project ID cannot be empty.")
        data = self._load_file()
        data[SELECTED_PROJECT_KEY] = project_id.strip()
        self._save_file(data)

    # ------------------------------------------------------------------
    # Resolved values (env > file > default)
    # ------------------------------------------------------------------

    @property
    def api_url(self) -> str:
        return self._env.get(ENV_API_URL) or self._load_file().get("api_url", DEFAULT_API_URL)

    @property
    def frontend_url(self) -> str:
        return self._env.get(ENV_FRONTEND_URL) or self._load_file().get(
            "frontend_url", DEFAULT_FRONTEND_URL
        )

    @property
    def api_url_source(self) -> str:
        if self._env.get(ENV_API_URL):
            return "environment"
        if "api_url" in self._load_file():
            return "config-file"
        return "default"

    def save_cli_session(self, data: dict[str, Any]) -> None:
        """Persist interactive CLI login tokens in the OS keyring (never in config.toml)."""
        self.secrets.set_token(json.dumps(data), username=CLI_SESSION_KEYRING_USER)
        self.secrets.delete_token()

    def load_cli_session(self) -> dict[str, Any] | None:
        raw = self.secrets.get_token(username=CLI_SESSION_KEYRING_USER)
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def clear_cli_session(self) -> None:
        self.secrets.delete_token(username=CLI_SESSION_KEYRING_USER)

    @property
    def cli_session(self) -> dict[str, Any] | None:
        return self.load_cli_session()

    @property
    def token(self) -> str | None:
        """Return credential: env API key > CLI session JWT > legacy keyring API key."""
        env_token = self._env.get(ENV_API_KEY) or self._env.get(ENV_API_TOKEN)
        if env_token:
            return env_token.strip() or None
        session = self.load_cli_session()
        if session and session.get("access_token"):
            return str(session["access_token"])
        return self.secrets.get_token()

    @property
    def token_source(self) -> str | None:
        if self._env.get(ENV_API_KEY) or self._env.get(ENV_API_TOKEN):
            return "environment"
        if self.load_cli_session():
            return "cli-session"
        if self.secrets.get_token():
            return "credentials-file" if self.secrets.using_fallback else "keyring"
        return None

    def update_cli_session(self, data: dict[str, Any]) -> None:
        self.save_cli_session(data)

    @property
    def is_using_api_key(self) -> bool:
        """True when the configured token is a DevArchAI API key (``sk-`` or legacy ``dk_``)."""
        token = self.token
        return bool(token and token.startswith(("sk-", "dk_")))

    @property
    def env_credential_set(self) -> bool:
        """True when ``DEVSEC_API_KEY`` or legacy ``DEVSEC_API_TOKEN`` is set in the env."""
        return bool(
            (self._env.get(ENV_API_KEY) or "").strip()
            or (self._env.get(ENV_API_TOKEN) or "").strip()
        )

    def api_url_display(self) -> str:
        """Display form of the API URL for user messages."""
        return self.api_url.rstrip("/")
