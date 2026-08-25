"""DevArchAI CLI entrypoint."""

from __future__ import annotations

import typer

from devsec.commands import auth_app, config_app, project_app, scan_app
from devsec.commands.base import command, set_debug
from devsec.commands.version import version_cmd
from devsec.output.console import is_ci, set_output_mode

app = typer.Typer(
    name="devsec",
    help="DevArchAI command-line interface - DevSecOps scanning for Infrastructure as Code.",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode="rich",
)


def _version_flag(value: bool) -> None:
    if value:
        version_cmd(json=False)
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_flag,
        is_eager=True,
        help="Show version and exit.",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Show full tracebacks on errors (never logs credentials).",
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Minimal output (implies --json in CI)."
    ),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output."),
) -> None:
    """DevArchAI CLI."""
    set_debug(debug)
    auto_quiet = quiet or is_ci()
    auto_no_color = no_color or auto_quiet or is_ci()
    set_output_mode(quiet=auto_quiet, no_color=auto_no_color)
    ctx.ensure_object(dict)
    ctx.obj["quiet"] = auto_quiet
    ctx.obj["no_color"] = auto_no_color


@app.command("version")
@command
def version_command(
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Print version information."""
    return version_cmd(json=json)


app.add_typer(config_app, name="config")
app.add_typer(auth_app, name="auth")
app.add_typer(project_app, name="project")
app.add_typer(scan_app, name="scan")


def entrypoint() -> None:
    """Console entry point (see pyproject ``[project.scripts]``)."""
    app()


if __name__ == "__main__":
    entrypoint()
