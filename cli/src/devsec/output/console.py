"""Console and output helpers.

Rules:

- Rich UI output goes to ``stdout`` only when NOT in ``--json`` mode.
- In ``--json`` mode the *only* thing written to ``stdout`` is the machine
  readable JSON payload - never log lines, progress, or panels.
- Diagnostics (warnings, debug, errors outside JSON payloads) go to
  ``stderr`` so they never corrupt a piped/parsed stdout stream.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme

# A single Console instance is created lazily so tests can capture cleanly.
console: Console | None = None

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


def get_console() -> Console:
    """Return the shared, themed console instance."""
    global console
    if console is None:
        console = Console(theme=THEME, highlight=False)
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
