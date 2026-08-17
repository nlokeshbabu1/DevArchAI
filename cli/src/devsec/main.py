"""DevArchAI CLI entrypoint."""

from __future__ import annotations

import typer

from devsec.commands import auth_app, config_app, project_app
from devsec.commands.base import command, set_debug
from devsec.commands.version import version_cmd

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
) -> None:
    """DevArchAI CLI."""
    set_debug(debug)


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


def entrypoint() -> None:
    """Console entry point (see pyproject ``[project.scripts]``)."""
    app()


if __name__ == "__main__":
    entrypoint()
