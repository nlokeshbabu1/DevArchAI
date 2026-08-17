"""Rich table builders for command output."""

from __future__ import annotations

from datetime import datetime

from rich.table import Table

from devsec.models.project import Project


def _fmt_dt(value: datetime | None) -> str:
    if value is None:
        return "-"
    try:
        return value.strftime("%Y-%m-%d %H:%M")
    except (AttributeError, ValueError):
        return str(value)


def _short_id(value: str) -> str:
    """Compact a long (UUID) repository ID for table display.

    Full IDs are unwieldy in tables and squeeze out more useful columns; the
    complete value is always available via ``devsec project list --json``.
    """
    return value[:8] if len(value) > 8 else value


def projects_table(projects: list[Project]) -> Table:
    """Render a list of projects (backend repositories) as a Rich table."""
    table = Table(title="Projects", show_lines=False, header_style="bold cyan")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Repository", style="bold")
    table.add_column("Provider", no_wrap=True)
    table.add_column("Branch", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Last Scan", no_wrap=True)
    table.add_column("Created", no_wrap=True)

    for project in projects:
        table.add_row(
            _short_id(project.id),
            project.repository,
            project.provider,
            project.default_branch,
            project.scan_status or "-",
            _fmt_dt(project.last_scan_at),
            _fmt_dt(project.created_at),
        )
    return table
