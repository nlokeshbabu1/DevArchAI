"""``devsec auth`` - authentication flows."""

from __future__ import annotations

import typer
from rich.table import Table

from devsec.api.auth import login as api_login, logout as api_logout, status as api_status
from devsec.commands.base import command, make_client
from devsec.output.console import get_console, print_muted, print_success

app = typer.Typer(
    help="Authenticate with the DevArchAI platform.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command("login")
@command
def auth_login(
    api_key: str | None = typer.Option(
        None, "--api-key", help="Provide the API key directly (skips the prompt)."
    ),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Authenticate with a DevArchAI API key."""
    config, client = make_client()
    try:
        data = api_login(config, client, api_key=api_key)
        if not json:
            email = data.get("email")
            if email:
                print_success(f"Logged in as {email}.")
            else:
                print_success("Logged in.")
        return data
    finally:
        client.close()


@app.command("logout")
@command
def auth_logout(
    revoke: bool = typer.Option(False, "--revoke", help="Also revoke the API key on the server."),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Remove the stored API key."""
    config, client = make_client()
    try:
        data = api_logout(config, client, revoke=revoke)
        if not json:
            print_success(
                f"Logged out. API key {'revoked' if data['revoked'] else 'removed locally'}."
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
            if data["authenticated"]:
                user = data["user"]
                print_success(f"Authenticated as {user['email']} (role: {user['role']})")
                table = Table(header_style="bold cyan")
                table.add_column("Property")
                table.add_column("Value")
                table.add_row("Source", data["token_source"])
                table.add_row("Plan", user["plan"])
                table.add_row("API key", "yes" if user["has_api_key"] else "no")
                get_console().print(table)
            else:
                print_muted("Not authenticated.")
                if data["error"]:
                    print_muted(f"Reason: {data['error']}")
                print_muted("Run 'devsec auth login' to authenticate.")
        return data
    finally:
        client.close()
