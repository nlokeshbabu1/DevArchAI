"""Console and output helpers.

Rules:

- Rich UI output goes to ``stdout`` only when NOT in ``--json`` mode.
- In ``--json`` mode the *only* thing written to ``stdout`` is the machine
  readable JSON payload - never log lines, progress, or panels.
- Diagnostics (warnings, debug, errors outside JSON payloads) go to
  ``stderr`` so they never corrupt a piped/parsed stdout stream.
"""

from __future__ import annotations

import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme

# A single Console instance is created lazily so tests can capture cleanly.
console: Console | None = None

# Widens the non-TTY fallback (default is 80) so data-dense tables such as
# ``devsec project list`` keep all their columns when piped to a file or in
# CI. Real terminals still auto-detect their own width.
_NON_TTY_WIDTH = 100

THEME = Theme(
    {
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "muted": "dim",
        "info": "cyan",
        "key": "bold",
    }
)

# Rich UI is disabled automatically when stdout is not a TTY. To force JSON
# mode, commands gate on their ``--json`` flag before calling render helpers.
_FORCE_PLAIN = False
_QUIET = False
_NO_COLOR = False


def set_output_mode(*, quiet: bool = False, no_color: bool = False) -> None:
    """Configure global output behaviour for CI and scripting."""
    global _QUIET, _NO_COLOR, console
    _QUIET = bool(quiet)
    _NO_COLOR = bool(no_color) or _QUIET
    console = None


def is_quiet() -> bool:
    return _QUIET


def is_no_color() -> bool:
    return _NO_COLOR or not sys.stdout.isatty()


def is_ci() -> bool:
    """True when running in a known CI environment."""
    markers = (
        "CI",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "JENKINS_URL",
        "BUILDKITE",
        "CIRCLECI",
        "TF_BUILD",
    )
    return any(os.environ.get(key) for key in markers)


def get_console(*, stderr: bool = False) -> Console:
    """Return the shared, themed console instance."""
    global console
    if console is None or stderr:
        stream = sys.stderr if stderr else sys.stdout
        width: int | None = _NON_TTY_WIDTH if not stream.isatty() else None
        instance = Console(
            theme=THEME,
            highlight=False,
            width=width,
            stderr=stderr,
            no_color=is_no_color(),
        )
        if stderr:
            return instance
        console = instance
    return console


def print_success(message: str) -> None:
    get_console().print(f"[success]✓[/success] {message}")


def print_error(message: str) -> None:
    get_console().print(f"[error]✗[/error] {message}")


def print_warning(message: str) -> None:
    get_console().print(f"[warning]⚠[/warning] {message}", style="warning")


def print_muted(message: str) -> None:
    get_console().print(message, style="muted")


def print_panel(message: str, title: str | None = None) -> None:
    get_console().print(Panel(message, title=title, border_style="info"))


def error_line(message: str) -> None:
    """Write a plain error line to stderr (for JSON mode diagnostics)."""
    from rich.console import Console as _Console

    _Console(stderr=True).print(message)
