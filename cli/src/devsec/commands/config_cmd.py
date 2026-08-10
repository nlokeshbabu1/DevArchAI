"""``devsec config`` - manage local configuration."""

from __future__ import annotations

from typing import Any

import typer
from rich.table import Table

from devsec.commands.base import command
from devsec.config import CONFIG_KEYS, Config
from devsec.output.console import get_console, print_success
from devsec.utils.errors import UsageError

app = typer.Typer(
    help="Manage local configuration.",
    no_args_is_help=True,
    add_completion=False,
)


def _config_list_data() -> dict[str, Any]:
    config = Config()
    return {
        "config_file": str(config.config_file),
        "values": config.file_values(),
        "api_url": config.api_url,
        "api_url_source": config.api_url_source,
        "frontend_url": config.frontend_url,
        "token_source": config.token_source,
    }


@app.command("list")
@command
def config_list(*, json: bool = typer.Option(False, "--json", help="Emit JSON to stdout.")) -> dict:
    """Show all configured values."""
    data = _config_list_data()
    if not json:
        config = Config()
        table = Table(title="Configuration", header_style="bold cyan")
        table.add_column("Key", style="bold")
        table.add_column("Value")
        for key, value in sorted(data["values"].items()):
            table.add_row(key, value)
        table.add_row("api_url (effective)", config.api_url)
        table.add_row("frontend_url (effective)", config.frontend_url)
        table.add_row("token_source", data["token_source"] or "none")
        get_console().print(table)
        print_success(f"Config file: {config.config_file}")
    return data


@app.command("show")
@command
def config_show(
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Alias for 'config list' - show all configured values."""
    return _config_list_data()


@app.command("get")
@command
def config_get(
    key: str,
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Show a single configuration value."""
    config = Config()
    mapped = CONFIG_KEYS.get(key)
    if mapped is None:
        raise UsageError(
            f"Unknown config key: {key}",
            hint=f"Valid keys: {', '.join(sorted(CONFIG_KEYS))}",
        )
    data = {"key": key, "value": config.file_values().get(mapped)}
    if not json:
        value = data["value"] if data["value"] is not None else "(unset)"
        print_success(f"{key} = {value}")
    return data


@app.command("set")
@command
def config_set(
    key: str,
    value: str,
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Set a configuration value (e.g. api-url, frontend-url)."""
    config = Config()
    config.set(key, value)
    data = {"key": key, "value": config.file_values().get(CONFIG_KEYS[key])}
    if not json:
        print_success(f"{key} set to {data['value']}")
    return data


@app.command("unset")
@command
def config_unset(
    key: str,
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Remove a configuration value."""
    config = Config()
    config.unset(key)
    data = {"key": key, "removed": True}
    if not json:
        print_success(f"{key} unset")
    return data
