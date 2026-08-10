"""Authentication API calls and login/logout flows.

The CLI authenticates with a *persistent API key* generated in the web app.
``devsec auth login`` opens the Settings page and stores the pasted key in the
OS keyring (or an env var / config for CI). This module deliberately does not
implement password-based or device-code OAuth.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

import typer

from devsec.api.client import ApiClient
from devsec.config import Config
from devsec.models.user import UserInfo
from devsec.utils.errors import AuthError, UsageError

API_KEY_PREFIX = "sk-"
LEGACY_API_KEY_PREFIX = "dk_"


def _is_api_key(token: str) -> bool:
    """True for current ``sk-`` keys and legacy ``dk_`` keys."""
    return token.startswith((API_KEY_PREFIX, LEGACY_API_KEY_PREFIX))


def _frontend_key_page(config: Config) -> str:
    """URL of the web app Settings page where API keys are managed."""
    return f"{config.frontend_url.rstrip('/')}/settings"


def _is_wsl() -> bool:
    """Detect Windows Subsystem for Linux."""
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        version = Path("/proc/version").read_text(errors="ignore")
    except OSError:
        return False
    return "microsoft" in version.lower()


def _run_launcher(argv: list[str]) -> bool:
    try:
        subprocess.run(argv, check=True, timeout=10, stderr=subprocess.DEVNULL)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def _open_browser(url: str) -> None:
    """Open a URL in the user's browser, degrading gracefully.

    - WSL has no Linux browser, so ``wslview`` (if installed) or
      ``explorer.exe`` (opens the Windows default browser) is used. The broken
      ``xdg-open`` is never spawned there, and if neither launcher works the
      URL is simply left for the caller to print.
    - Any failure is swallowed - the caller always prints the URL so the user
      can open it manually.
    """
    if _is_wsl():
        for launcher in ("wslview", "explorer.exe"):
            exe = shutil.which(launcher)
            if exe and _run_launcher([exe, url]):
                return
        return
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001, S110 - a failed open must never abort login
        pass


def login(config: Config, client: ApiClient, *, api_key: str | None = None) -> dict:
    """Authenticate with an API key, storing it securely on success."""
    if api_key is None:
        if sys.stdin.isatty():
            key_page = _frontend_key_page(config)
            print(
                typer.style(
                    "Opening the DevArchAI web app to generate an API key...",
                    fg="cyan",
                ),
                file=sys.stderr,
            )
            _open_browser(key_page)
            print(
                typer.style(
                    f"If a browser did not open, copy this URL into any browser: {key_page}",
                    dim=True,
                ),
                file=sys.stderr,
            )
            api_key = typer.prompt(
                "Paste your API key (create one under Settings > Security)",
                hide_input=True,
            )
        else:
            raise UsageError(
                "No API key provided.",
                hint="Pass one with 'devsec auth login --api-key sk-...' or set "
                "the DEVSEC_API_KEY environment variable.",
            )

    api_key = (api_key or "").strip()
    if not api_key:
        raise UsageError("API key cannot be empty.")
    if not _is_api_key(api_key):
        key_page = _frontend_key_page(config)
        raise UsageError(
            "That does not look like a DevArchAI API key.",
            hint=f"API keys start with '{API_KEY_PREFIX}'. Generate one under "
            f"Settings > Security in the web app: {key_page}",
        )

    # Validate against the backend before persisting anything.
    email: str | None = None
    if config.token != api_key:
        payload = ApiClient(config, token=api_key).get_json("/auth/me")
        email = (payload or {}).get("email")

    config.secrets.set_token(api_key)
    return {
        "stored": True,
        "token_source": "keyring",
        "key_prefix": api_key[:6],
        "email": email,
    }


def logout(config: Config, client: ApiClient, *, revoke: bool = False) -> dict:
    """Remove the stored token, optionally revoking the API key server-side."""
    token = config.token
    revoked = False
    if revoke and token and config.is_using_api_key:
        if token.startswith(API_KEY_PREFIX):
            client.delete("/settings/api-keys/current")
        else:
            client.delete("/auth/api-key")
        revoked = True
    config.secrets.delete_token()
    return {"logged_out": True, "revoked": revoked}


def status(config: Config, client: ApiClient) -> dict:
    """Report authentication state and, when authenticated, the current user."""
    token = config.token
    if not token:
        return {
            "authenticated": False,
            "token_source": None,
            "api_url": config.api_url_display(),
            "user": None,
            "error": None,
        }
    source = config.token_source or "unknown"
    user: UserInfo | None = None
    error: str | None = None
    try:
        payload = client.get_json("/auth/me")
        user = UserInfo.model_validate(payload)
    except AuthError as exc:
        error = exc.message
    return {
        "authenticated": user is not None,
        "token_source": source,
        "api_url": config.api_url_display(),
        "user": user.model_dump() if user else None,
        "error": error,
    }
