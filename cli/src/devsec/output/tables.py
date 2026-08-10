"""Rich table builders for command output."""

from __future__ import annotations

from rich.table import Table

from devsec.models.project import Project

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def projects_table(projects: list[Project]) -> Table:
    """Render a list of projects (backend repositories) as a Rich table."""
    table = Table(title="Projects", show_lines=False, header_style="bold cyan")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Default Branch", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Score")
    table.add_column("Issues", no_wrap=True)
    table.add_column("Last Scanned", no_wrap=True)

    for project in projects:
        issues = project.issues or {}
        issue_label = "".join(
            f"[{color}]{severity}:{issues.get(severity, 0)}[/{color}] "
            for severity, color in (
                ("critical", "red"),
                ("high", "orange1"),
                ("medium", "yellow"),
                ("low", "green"),
            )
        )
        score = f"{project.overall_score:.0f}" if project.overall_score is not None else "-"
        last_scanned = (
            project.last_scan_at.strftime("%Y-%m-%d %H:%M") if project.last_scan_at else "-"
        )
        table.add_row(
            project.id,
            project.name,
            project.default_branch,
            project.scan_status or "-",
            score,
            issue_label or "-",
            last_scanned,
        )
    return table
