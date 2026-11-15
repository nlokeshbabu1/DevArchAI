"""Authentication API calls and login/logout flows.

Interactive login uses PKCE + browser authorization (``devsec login``).
API keys remain supported for CI/CD (``--api-key`` or ``DEVSEC_API_KEY``).
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
from devsec.utils.errors import ApiError, AuthError, UsageError

API_KEY_PREFIX = "sk-"
LEGACY_API_KEY_PREFIX = "dk_"


def _is_api_key(token: str) -> bool:
    """True for current ``sk-`` keys and legacy ``dk_`` keys."""
    return token.startswith((API_KEY_PREFIX, LEGACY_API_KEY_PREFIX))


def authentication_method(token: str | None, *, config: Config | None = None) -> str | None:
    """Human-readable authentication method label (never includes the secret)."""
    if config and config.cli_session and not config.env_credential_set:
        return "CLI Session"
    if not token:
        return None
    if _is_api_key(token):
        return "API Key"
    return "Bearer Token"


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


def _prompt_login_method() -> str:
    """Ask whether to use the browser flow or a pasted API key."""
    stderr = sys.stderr
    print(typer.style("\nHow would you like to sign in?\n", fg="cyan"), file=stderr)
    print("  1) Open the browser and sign in (recommended)", file=stderr)
    print("  2) Paste an API key from the web app", file=stderr)
    while True:
        choice = typer.prompt("Selection", default="1", show_default=False, err=True)
        normalized = str(choice).strip().lower()
        if normalized in {"1", "b", "browser"}:
            return "browser"
        if normalized in {"2", "a", "api", "api-key", "api_key", "key", "k"}:
            return "api_key"
        print("Enter 1 for the browser or 2 for an API key.", file=stderr)


def _prompt_api_key(config: Config) -> str:
    """Show where to create an API key and read it with hidden input."""
    key_page = _frontend_key_page(config)
    stderr = sys.stderr
    print("\nCreate an API key in the web app:", file=stderr)
    print(f"  Settings > Security: {key_page}\n", file=stderr)
    return str(typer.prompt("Paste your API key (input hidden)", hide_input=True, err=True))


def login(
    config: Config,
    client: ApiClient,
    *,
    api_key: str | None = None,
    server: str | None = None,
    device_name: str | None = None,
) -> dict:
    """Authenticate via browser login or an explicit API key."""
    if api_key is None:
        if not sys.stdin.isatty():
            raise UsageError(
                "No credentials available for non-interactive login.",
                hint="Set DEVSEC_API_KEY for CI/CD or pass --api-key.",
            )
        if _prompt_login_method() == "browser":
            from devsec.auth.browser_login import browser_login

            return browser_login(config, server=server, device_name=device_name)
        api_key = _prompt_api_key(config)

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

    # Always validate against the backend before persisting anything.
    # Never log or echo the key.
    validate_client = ApiClient(config, token=api_key)
    try:
        payload = validate_client.get_json("/auth/me")
        email = (payload or {}).get("email")
    finally:
        validate_client.close()

    config.secrets.set_token(api_key)
    stored_source = "credentials-file" if config.secrets.using_fallback else "keyring"
    return {
        "stored": True,
        "token_source": stored_source,
        "email": email,
        "api_url": config.api_url_display(),
        "authentication": "API Key",
    }


def logout(config: Config, client: ApiClient, *, revoke: bool = True) -> dict:
    """Clear local credentials and revoke CLI session or API key when possible."""
    stored = config.secrets.get_token()
    cli_session = config.load_cli_session()
    effective = config.token
    revoked = False
    if revoke and cli_session and cli_session.get("refresh_token") and not config.env_credential_set:
        revoke_client = ApiClient(config)
        try:
            revoke_client.post_json(
                "/auth/cli/revoke",
                {"refresh_token": cli_session["refresh_token"]},
            )
            revoked = True
        except Exception:  # noqa: BLE001, S110
            pass
        finally:
            revoke_client.close()
        config.clear_cli_session()

    revoke_token = stored or effective
    if revoke and revoke_token and _is_api_key(revoke_token):
        revoke_client = ApiClient(config, token=revoke_token)
        try:
            if revoke_token.startswith(API_KEY_PREFIX):
                revoke_client.delete("/settings/api-keys/current")
            else:
                revoke_client.delete("/auth/api-key")
            revoked = True
        finally:
            revoke_client.close()

    config.secrets.delete_token()
    config.clear_cli_session()
    return {
        "logged_out": True,
        "revoked": revoked,
        "env_credential_still_set": config.env_credential_set,
    }


def status(config: Config, client: ApiClient) -> dict:
    """Report authentication state and, when authenticated, the current user."""
    token = config.token
    api_url = config.api_url_display()
    if not token:
        return {
            "authenticated": False,
            "token_source": None,
            "api_url": api_url,
            "authentication": None,
            "account": None,
            "user": None,
            "error": None,
        }

    source = config.token_source or "unknown"
    method = authentication_method(token, config=config)
    user: UserInfo | None = None
    error: str | None = None
    try:
        payload = client.get_json("/auth/me")
        user = UserInfo.model_validate(payload)
    except AuthError as exc:
        error = exc.message
    except ApiError as exc:
        # Network/timeout/5xx during validation - report as not authenticated
        # with a clear reason rather than crashing the status command.
        error = exc.message

    account = None
    if user is not None:
        account = user.email or user.username or user.id

    session = config.cli_session or {}
    return {
        "authenticated": user is not None,
        "token_source": source,
        "api_url": api_url,
        "authentication": method,
        "account": account,
        "user": user.model_dump() if user else None,
        "error": error,
        "device_name": session.get("device_name"),
        "credential_expires_at": session.get("expires_at"),
    }
