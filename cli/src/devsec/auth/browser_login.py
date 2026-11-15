"""Interactive browser-based CLI login (PKCE + loopback)."""

from __future__ import annotations

import socket
import sys
import time

import httpx
import typer

from devsec.api.auth import _open_browser
from devsec.auth.callback_server import LoopbackCallbackServer
from devsec.auth.pkce import challenge_from_verifier, generate_state, generate_verifier
from devsec.config import Config
from devsec.utils.errors import ApiError, AuthError, UsageError

_API_PREFIX = "/api/v1"


def _default_device_name() -> str:
    return socket.gethostname() or "DevArchAI CLI"


def browser_login(
    config: Config,
    *,
    server: str | None = None,
    device_name: str | None = None,
    timeout: float = 300.0,
) -> dict:
    """Run PKCE loopback login; store CLI session in the OS keyring."""
    api_base = (server or config.api_url).rstrip("/")
    verifier = generate_verifier()
    challenge = challenge_from_verifier(verifier)
    state = generate_state()
    device = (device_name or _default_device_name()).strip() or _default_device_name()

    listener = LoopbackCallbackServer()
    listener.start()
    redirect_uri = listener.redirect_uri

    register_body = {
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "redirect_uri": redirect_uri,
        "device_name": device,
    }

    with httpx.Client(base_url=api_base, timeout=30.0) as http:
        try:
            reg = http.post(f"{_API_PREFIX}/auth/cli/register", json=register_body)
            reg.raise_for_status()
        except httpx.HTTPError as exc:
            listener.stop()
            raise ApiError(
                "Unable to start CLI login with the DevArchAI API.",
                hint="Check the API URL and your network connection.",
            ) from exc
        reg_data = reg.json()
        authorize_url = reg_data["authorize_url"]
        session_id = reg_data["session_id"]

    print(typer.style("DevArchAI CLI", bold=True), file=sys.stderr)
    print(typer.style("\nOpening browser for authentication...\n", fg="cyan"), file=sys.stderr)
    _open_browser(authorize_url)
    print(
        typer.style(f"If a browser did not open, visit:\n{authorize_url}\n", dim=True),
        file=sys.stderr,
    )
    print(typer.style("Waiting for authorization...\n", fg="cyan"), file=sys.stderr)

    try:
        callback_result = listener.wait(timeout=timeout)
    except TimeoutError as exc:
        raise UsageError(
            "Authorization timed out.",
            hint="Run `devsec login` and complete sign-in in the browser within a few minutes.",
        ) from exc
    except RuntimeError as exc:
        if str(exc) == "cancelled":
            raise UsageError("Login was cancelled.", hint="Run `devsec login` to try again.") from exc
        raise UsageError("Login failed.", hint="Run `devsec login` to try again.") from exc

    if callback_result.state != state:
        raise AuthError("Login failed due to invalid state.", hint="Run `devsec login` to try again.")

    token_body = {
        "session_id": session_id,
        "state": state,
        "code": callback_result.code,
        "code_verifier": verifier,
    }
    with httpx.Client(base_url=api_base, timeout=30.0) as http:
        try:
            tok = http.post(f"{_API_PREFIX}/auth/cli/token", json=token_body)
            if tok.status_code >= 400:
                raise AuthError(
                    "Could not complete CLI login.",
                    hint="Run `devsec login` to try again.",
                    status_code=tok.status_code,
                )
        except httpx.HTTPError as exc:
            raise ApiError("Unable to reach the DevArchAI API during login.") from exc
        payload = tok.json()

    expires_in = int(payload.get("expires_in", 900))
    config.save_cli_session(
        {
            "access_token": payload["access_token"],
            "refresh_token": payload["refresh_token"],
            "expires_at": time.time() + expires_in,
            "session_id": payload.get("session_id"),
            "email": payload.get("email"),
            "device_name": device,
        }
    )
    if server:
        config.set("api-url", server)
    return {
        "stored": True,
        "email": payload.get("email"),
        "api_url": api_base,
        "authentication": "CLI Session",
        "token_source": "cli-session",
        "device_name": device,
    }