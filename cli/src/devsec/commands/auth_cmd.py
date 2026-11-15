"""``devsec auth`` - authentication flows."""

from __future__ import annotations

import typer

from devsec.api.auth import login as api_login, logout as api_logout, status as api_status
from devsec.commands.base import command, make_client
from devsec.output.console import get_console, print_muted, print_success, print_warning

app = typer.Typer(
    help="Authenticate with the DevArchAI platform.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command("login")
@command
def auth_login(
    api_key: str | None = typer.Option(
        None, "--api-key", help="Use an API key instead of browser login (CI/automation)."
    ),
    server: str | None = typer.Option(
        None, "--server", help="Custom DevArchAI API base URL (https required except localhost)."
    ),
    device_name: str | None = typer.Option(None, "--device-name", help="Label for this CLI device."),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Sign in with your DevArchAI account (browser) or an API key."""
    config, client = make_client()
    try:
        data = api_login(config, client, api_key=api_key, server=server, device_name=device_name)
        if not json:
            email = data.get("email")
            if data.get("authentication") == "CLI Session":
                print_success("Authentication successful")
                if email:
                    print_success(f"Account: {email}")
                print_muted(f"API: {data.get('api_url')}")
                print_muted("Credentials stored securely (never written to config.toml).")
            elif email:
                print_success(f"Logged in as {email}.")
            else:
                print_success("Logged in.")
            print_muted(f"API: {data.get('api_url')}")
        return data
    finally:
        client.close()


@app.command("logout")
@command
def auth_logout(
    revoke: bool = typer.Option(True, "--revoke/--no-revoke", help="Revoke the server-side CLI session/API key."),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Remove the stored API key from the local keyring."""
    config, client = make_client()
    try:
        data = api_logout(config, client, revoke=revoke)
        if not json:
            if data["revoked"]:
                print_success("Logged out. API key revoked on the server and removed locally.")
            else:
                print_success("Logged out. Local credential removed.")
            if data.get("env_credential_still_set"):
                print_warning(
                    "DEVSEC_API_KEY (or DEVSEC_API_TOKEN) is still set in this environment "
                    "and will continue to authenticate until you unset it."
                )
        return data
    finally:
        client.close()


@app.command("status")
@command
def auth_status(
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Show authentication status and the current user."""
    config, client = make_client()
    try:
        data = api_status(config, client)
        if not json:
            console = get_console()
            if data["authenticated"]:
                print_success("Authenticated")
                console.print("")
                console.print(f"[key]Account:[/key] {data.get('account') or 'unknown'}")
                console.print(f"[key]API:[/key] {data['api_url']}")
                console.print(
                    f"[key]Authentication:[/key] {data.get('authentication') or 'unknown'}"
                )
                if data.get("token_source"):
                    console.print(f"[key]Source:[/key] {data['token_source']}")
            else:
                print_muted("Not authenticated.")
                console.print(f"[key]API:[/key] {data['api_url']}")
                if data.get("authentication"):
                    console.print(
                        f"[key]Authentication:[/key] {data['authentication']} (invalid or unreachable)"
                    )
                if data["error"]:
                    print_muted(f"Reason: {data['error']}")
                print_muted("Run 'devsec auth login' to authenticate.")
        return data
    finally:
        client.close()
