"""``devsec project`` - manage projects (backend repositories)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from rich.table import Table

from devsec.api.projects import create_project, get_project, list_projects, resolve_project
from devsec.commands.base import command, make_client
from devsec.models.project import Project
from devsec.output.console import get_console, print_muted, print_success
from devsec.output.tables import projects_table
from devsec.utils.detect import detect_stack
from devsec.utils.errors import UsageError
from devsec.utils.filesystem import project_summary
from devsec.utils.git import get_git_metadata

app = typer.Typer(
    help="Manage projects (backed by the DevArchAI repositories API).",
    no_args_is_help=True,
    add_completion=False,
)


@app.command("list")
@command
def project_list(
    page: int = typer.Option(1, "--page", help="Page number."),
    page_size: int = typer.Option(20, "--page-size", help="Results per page."),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """List your projects."""
    _, client = make_client()
    try:
        result = list_projects(client, page=page, page_size=page_size)
        data = {
            "projects": [p.model_dump() for p in result.projects],
            "total": result.total,
            "page": result.page,
            "page_size": result.page_size,
        }
        if not json:
            if result.projects:
                get_console().print(projects_table(result.projects))
                print_muted(
                    f"{result.total} total - page {result.page} of "
                    f"{(result.total + result.page_size - 1) // result.page_size or 1}"
                )
                print_muted(
                    "Tip: pass an ID prefix to select (e.g. devsec project select ae8f8620) "
                    "or use --json for full UUIDs."
                )
            else:
                print_muted("No projects found.")
        return data
    finally:
        client.close()


@app.command("show")
@command
def project_show(
    project_id: str,
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Show a single project by ID."""
    _, client = make_client()
    try:
        project = resolve_project(client, project_id)
        data = project.model_dump()
        if not json:
            _render_project(project)
        return data
    finally:
        client.close()


@app.command("select")
@command
def project_select(
    project_id: str,
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Select a project as the current project (stored locally)."""
    config, client = make_client()
    try:
        project = resolve_project(client, project_id)
        config.set_selected_project(project.id)
        data = project.model_dump()
        if not json:
            print_success(f"Selected project: {project.name} ({project.id})")
        return data
    finally:
        client.close()


@app.command("current")
@command
def project_current(
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Show the currently selected project."""
    config, client = make_client()
    try:
        project_id = config.selected_project
        if not project_id:
            data: dict[str, Any] = {"selected": None, "project": None}
            if not json:
                print_muted("No project selected.")
                print_muted("")
                print_muted('Use: "devsec project select <id>"')
                print_muted("to select one.")
            return data
        project = get_project(client, project_id)
        data = {"selected": project.id, "project": project.model_dump()}
        if not json:
            _render_project(project)
        return data
    finally:
        client.close()


@app.command("create")
@command
def project_create(
    url: str,
    name: str | None = typer.Option(
        None, "--name", help="Project name (auto-detected if omitted)."
    ),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Register a repository URL as a project."""
    _, client = make_client()
    try:
        project = create_project(client, url, name=name)
        data = project.model_dump()
        if not json:
            print_success(f"Project created: {project.name} ({project.id})")
        return data
    finally:
        client.close()


@app.command("add")
@command
def project_add(
    url: str,
    name: str | None = typer.Option(
        None, "--name", help="Project name (auto-detected if omitted)."
    ),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Alias for 'project create' - register a repository URL as a project."""
    _, client = make_client()
    try:
        project = create_project(client, url, name=name)
        data = project.model_dump()
        if not json:
            print_success(f"Project added: {project.name} ({project.id})")
        return data
    finally:
        client.close()


@app.command("detect")
@command
def project_detect(
    path: str = typer.Argument(".", help="Path to a local git repository."),
    register: bool = typer.Option(
        False, "--register", help="Also register the detected remote URL as a project."
    ),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Detect the technology stack in a local repository (no upload)."""
    root = Path(path).expanduser()
    if not root.is_dir():
        raise UsageError(f"Not a directory: {root}")

    git = get_git_metadata(root)
    summary = project_summary(root)
    stack = detect_stack(str(root))

    data = {
        "path": str(root.resolve()),
        "git": git.model_dump(exclude_none=True),
        "summary": summary,
        "stack": stack.model_dump(exclude_none=True),
        "registered": None,
    }

    if register:
        remote_url = git.require_remote()
        _, client = make_client()
        try:
            project = create_project(client, remote_url, name=git.display_name)
            data["registered"] = project.model_dump()
        finally:
            client.close()

    if not json:
        _render_detection(git, summary, stack, registered=data["registered"])
    return data


def _render_project(project: Project) -> None:
    table = Table(title=project.repository, header_style="bold cyan")
    table.add_column("Property")
    table.add_column("Value")
    table.add_row("ID", project.id)
    table.add_row("Repository", project.repository)
    table.add_row("Provider", project.provider)
    table.add_row("URL", project.url)
    table.add_row("Branch", project.default_branch)
    table.add_row("Status", project.scan_status or "-")
    if project.last_scan_at:
        table.add_row("Last scan", project.last_scan_at.strftime("%Y-%m-%d %H:%M"))
    if project.created_at:
        table.add_row("Created", project.created_at.strftime("%Y-%m-%d %H:%M"))
    score = f"{project.overall_score:.0f}" if project.overall_score is not None else None
    if score is not None:
        table.add_row("Overall score", score)
    if project.tech_stack:
        table.add_row("Tech stack", ", ".join(project.tech_stack))
    issues = project.issues or {}
    if issues:
        table.add_row(
            "Issues",
            ", ".join(f"{sev}:{count}" for sev, count in issues.items()),
        )
    get_console().print(table)


def _render_detection(git, summary, stack, registered) -> None:
    print_success(f"Analyzed {summary['root']}")
    print_muted(
        f"{summary['file_count']} files, {summary['total_size_bytes'] / 1024 / 1024:.1f} MiB"
    )
    if git.is_git:
        print_muted(f"Git: {git.branch or 'unknown'} @ {git.commit_sha or 'unknown'}")
        if git.remote_url:
            print_muted(f"Remote: {git.remote_url}")
    table = Table(title="Detected technologies", header_style="bold cyan")
    table.add_column("Technology")
    table.add_column("Files")
    for tech in stack.technologies:
        paths = getattr(stack, f"{tech}_files")
        table.add_row(tech, str(len(paths)))
    get_console().print(table)
    if stack.languages:
        print_muted(f"Languages: {', '.join(stack.languages)}")
    if registered:
        print_success(f"Registered project: {registered['name']} ({registered['id']})")
