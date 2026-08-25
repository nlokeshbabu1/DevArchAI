"""``devsec scan`` - start scans and inspect progress/results."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from devsec.api.progress import ProgressTracker
from devsec.api.projects import (
    get_project,
    list_projects,
    resolve_or_register_by_url,
    resolve_project,
)
from devsec.api.scans import (
    ensure_scan_completed,
    evaluate_scan_outcome,
    get_scan_results,
    get_scan_status,
    start_scan,
)
from devsec.commands.base import command, make_client
from devsec.config import Config
from devsec.models.project import Project
from devsec.models.scan import ScanResultsResponse, ScanStateResponse, ScanStatusResponse
from devsec.output.console import get_console, is_ci, print_error, print_muted, print_success
from devsec.output.json import emit
from devsec.output.progress_display import format_technology_label
from devsec.output.tables import findings_table, scan_summary_table
from devsec.utils.errors import ApiError, DevSecError, ExitCode, PolicyViolationError, UsageError
from devsec.utils.git import get_git_metadata

app = typer.Typer(
    help="Run security scans and inspect results.",
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False,
)


def _ctx_flags(ctx: typer.Context) -> tuple[bool, bool]:
    obj = ctx.obj or {}
    return bool(obj.get("json")), bool(obj.get("quiet"))


@app.callback()
def scan_group(
    ctx: typer.Context,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output."),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output."),
    project_id: str | None = typer.Option(
        None,
        "--project",
        "-p",
        help="Project (repository) ID to scan.",
    ),
    repo: str | None = typer.Option(
        None,
        "--repo",
        "-r",
        help="Repository URL to scan (registers with backend if needed).",
    ),
    path: str = typer.Option(
        ".",
        "--path",
        help="Path to a local git repository (uses origin/upstream remote).",
    ),
    branch: str | None = typer.Option(
        None,
        "--branch",
        "-b",
        help="Branch to scan (uses project default or local git branch if omitted).",
    ),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for scan completion."),
    fail_on: str = typer.Option(
        "high",
        "--fail-on",
        help="Exit 1 when findings at/above this severity exist.",
    ),
    include_ai: bool = typer.Option(
        True,
        "--include-ai/--no-ai",
        help="Wait for AI remediation recommendations after the scan.",
    ),
) -> None:
    """Shared options for scan commands."""
    from devsec.commands.base import _report_error, _report_unexpected
    from devsec.output.console import set_output_mode

    auto_json = json or quiet or is_ci()
    auto_quiet = quiet or is_ci()
    auto_no_color = no_color or auto_quiet or is_ci()
    set_output_mode(quiet=auto_quiet, no_color=auto_no_color)
    ctx.ensure_object(dict)
    ctx.obj["json"] = auto_json
    ctx.obj["quiet"] = auto_quiet
    ctx.obj["no_color"] = auto_no_color

    if ctx.invoked_subcommand is not None:
        return

    try:
        result = _run_scan(
            project_id=project_id,
            repo=repo,
            path=path,
            branch=branch,
            wait=wait,
            fail_on=fail_on,
            include_ai=include_ai,
            json_mode=auto_json,
            quiet_mode=auto_quiet,
        )
        if auto_json and result is not None:
            emit(result)
    except typer.Exit:
        raise
    except DevSecError as exc:
        _report_error(exc, auto_json)
        raise typer.Exit(int(exc.exit_code)) from None
    except Exception as exc:  # noqa: BLE001
        _report_unexpected(exc, auto_json)
        raise typer.Exit(2) from None


def _is_uuid(value: str) -> bool:
    import uuid

    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def _resolve_scan_branch(
    branch_flag: str | None,
    *,
    project: Project,
    git_branch: str | None = None,
) -> str:
    """Pick scan branch from flag, project default, or local git — never hardcode main/master."""
    if branch_flag and branch_flag.strip():
        return branch_flag.strip()
    if project.default_branch and project.default_branch.strip():
        return project.default_branch.strip()
    if git_branch and git_branch.strip() and git_branch != "HEAD":
        return git_branch.strip()
    short_id = project.id[:8]
    raise UsageError(
        "Branch not specified.",
        hint=(
            f'Pass --branch <name> (e.g. devsec scan --project {short_id} --branch <branch>) '
            f"or set the project default branch:\n"
            f"  devsec project set-branch {short_id} <branch>"
        ),
    )


def _resolve_scan_target(
    config: Config,
    client,
    *,
    project_id: str | None,
    repo: str | None,
    path: str,
    branch: str | None,
) -> tuple[Project, str]:
    if repo:
        project = resolve_or_register_by_url(client, repo.strip())
        scan_branch = _resolve_scan_branch(branch, project=project)
        return project, scan_branch

    explicit_id = (project_id or "").strip()
    if explicit_id:
        project = resolve_project(client, explicit_id)
        config.set_selected_project(project.id)
        scan_branch = _resolve_scan_branch(branch, project=project)
        return project, scan_branch

    selected = (config.selected_project or "").strip()
    if selected:
        try:
            project = get_project(client, selected) if _is_uuid(selected) else resolve_project(client, selected)
            scan_branch = _resolve_scan_branch(branch, project=project)
            return project, scan_branch
        except ApiError as exc:
            if exc.status_code != 404:
                raise
            # Stale selection — continue to auto-select or git detection.

    listing = list_projects(client, page_size=100)
    if len(listing.projects) == 1:
        project = listing.projects[0]
        config.set_selected_project(project.id)
        scan_branch = _resolve_scan_branch(branch, project=project)
        return project, scan_branch

    if listing.projects:
        prefixes = ", ".join(p.id[:8] for p in listing.projects[:3])
        raise UsageError(
            "No project selected.",
            hint=(
                f'Run "devsec project select <id>" (available: {prefixes}) '
                'or "devsec scan --repo <url>".'
            ),
        )

    git = get_git_metadata(path)
    remote_url = git.require_remote()
    project = resolve_or_register_by_url(client, remote_url, name=git.display_name)
    config.set_selected_project(project.id)
    scan_branch = _resolve_scan_branch(branch, project=project, git_branch=git.branch)
    return project, scan_branch


def _run_scan(
    *,
    project_id: str | None,
    repo: str | None,
    path: str,
    branch: str | None,
    wait: bool,
    fail_on: str,
    include_ai: bool,
    json_mode: bool,
    quiet_mode: bool,
) -> dict[str, Any]:
    config, client = make_client()
    try:
        project, scan_branch = _resolve_scan_target(
            config,
            client,
            project_id=project_id,
            repo=repo,
            path=path,
            branch=branch,
        )
        start = start_scan(
            client,
            repository_url=project.url,
            repository_id=project.id,
            branch=scan_branch,
            include_ai=include_ai,
        )

        repository_id = start.repository_id or project.id
        data: dict[str, Any] = {
            "scan_id": start.scan_id,
            "status": start.status,
            "repository_id": repository_id,
            "repository_url": start.repository_url or project.url,
            "repository_name": project.repository,
            "branch": start.branch or scan_branch,
            "message": start.message,
            "scan_url": _scan_url(config, start.scan_id),
            "history_url": _history_url(config),
            "results_url": _scan_url(config, start.scan_id),
            "repository_results_url": _repository_results_url(config, repository_id),
        }

        if not json_mode and not quiet_mode:
            print_success(f"Scan started: {start.scan_id}")
            print_muted(f"Repository: {project.repository}")
            if start.message:
                print_muted(start.message)

        if not wait:
            if not json_mode and not quiet_mode:
                print_muted(f"View in DevArchAI: {data['scan_url']}")
            return data

        tracker = ProgressTracker(
            client,
            start.scan_id,
            wait_for_ai=include_ai,
        )

        def on_update(_state) -> None:
            pass

        final_state = tracker.wait(on_update=on_update)
        ensure_scan_completed(
            ScanStatusResponse(
                scan_id=start.scan_id,
                status=final_state.status,
                progress=final_state.progress or 100,
                current_step=final_state.message,
                error_message=final_state.error_message,
            )
        )
        results = get_scan_results(client, start.scan_id)
        passed, reason = evaluate_scan_outcome(results, fail_on=fail_on)

        data.update(
            {
                "final_status": final_state.model_dump(),
                "results": results.model_dump(),
                "passed": passed,
                "policy_reason": reason,
                "ai_status": final_state.ai_status,
            }
        )

        if not json_mode:
            _render_results(
                results,
                project=project,
                scan_id=start.scan_id,
                repository_id=repository_id,
                config=config,
                final_state=final_state,
                passed=passed,
                reason=reason,
            )

        if not passed and reason:
            if json_mode:
                emit(data)
                raise typer.Exit(int(ExitCode.POLICY_VIOLATION))
            raise PolicyViolationError(reason or "Policy check failed.")
        return data
    finally:
        client.close()


def _scan_url(config: Config, scan_id: str) -> str:
    return f"{config.frontend_url.rstrip('/')}/scans/{scan_id}"


def _history_url(config: Config) -> str:
    return f"{config.frontend_url.rstrip('/')}/history"


def _repository_results_url(config: Config, repository_id: str) -> str:
    return f"{config.frontend_url.rstrip('/')}/repositories/{repository_id}/results"


def _results_url(config: Config, repository_id: str) -> str:
    """Deprecated alias — prefer _scan_url for per-scan links."""
    return _repository_results_url(config, repository_id)


@app.command("status")
@command
def scan_status_cmd(
    ctx: typer.Context,
    scan_id: str = typer.Argument(..., help="Scan ID (UUID)."),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output."),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output."),
) -> dict:
    """Show progress for a scan."""
    json_mode = json or bool((ctx.obj or {}).get("json"))
    _, client = make_client()
    try:
        status = get_scan_status(client, scan_id)
        data = status.model_dump()
        if not json_mode:
            _render_status(status)
        return data
    finally:
        client.close()


@app.command("results")
@command
def scan_results_cmd(
    ctx: typer.Context,
    scan_id: str = typer.Argument(..., help="Scan ID (UUID)."),
    fail_on: str = typer.Option(
        "high",
        "--fail-on",
        help="Exit 1 when findings at/above this severity exist.",
    ),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output."),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output."),
) -> dict:
    """Fetch and display findings for a completed scan."""
    json_mode = json or bool((ctx.obj or {}).get("json"))
    config, client = make_client()
    try:
        results = get_scan_results(client, scan_id)
        passed, reason = evaluate_scan_outcome(results, fail_on=fail_on)
        data = {
            **results.model_dump(),
            "passed": passed,
            "policy_reason": reason,
        }
        if not json_mode:
            _render_results(
                results,
                project=None,
                scan_id=scan_id,
                repository_id=None,
                config=config,
                final_state=None,
                passed=passed,
                reason=reason,
            )
        if not passed and reason:
            if json_mode:
                emit(data)
                raise typer.Exit(int(ExitCode.POLICY_VIOLATION))
            raise PolicyViolationError(reason or "Policy check failed.")
        return data
    finally:
        client.close()


def _render_status(status: ScanStatusResponse) -> None:
    get_console().print(scan_summary_table(status))


def _render_results(
    results: ScanResultsResponse,
    *,
    project: Project | None,
    scan_id: str,
    repository_id: str | None,
    config: Config,
    final_state: ScanStateResponse | None,
    passed: bool,
    reason: str | None,
) -> None:
    if passed:
        print_success("Scan completed ✓")
    else:
        print_error(reason or "Scan failed policy check.")

    repo_name = results.repository_name or (project.repository if project else "repository")
    print_muted("")
    print_muted(f"Repository: {repo_name}")
    print_muted(f"Scan ID: {scan_id}")

    tech_counts: dict[str, int] = {}
    if final_state and final_state.technology_items:
        for tech in final_state.technology_items:
            tech_counts[format_technology_label(tech.id, tech.name)] = tech.findings
    elif results.detected_technologies:
        for tech_id in results.detected_technologies:
            tech_counts[format_technology_label(tech_id)] = 0

    if tech_counts:
        print_muted("")
        print_muted("Technologies")
        for name, count in sorted(tech_counts.items()):
            label = "finding" if count == 1 else "findings"
            print_muted(f"  {name:<18} {count} {label}")

    risk = results.risk_distribution or results.severity_counts
    if risk:
        print_muted("")
        print_muted("Risk")
        for level in ("critical", "high", "medium", "low", "info"):
            count = risk.get(level) or risk.get(level.upper()) or 0
            if count:
                print_muted(f"  {level.capitalize():<10} {count}")

    repo_id = repository_id or (project.id if project else None)
    print_muted("")
    print_muted("View scan:")
    print_muted(_scan_url(config, scan_id))
    if repo_id:
        print_muted("Repository results:")
        print_muted(_repository_results_url(config, repo_id))
    print_muted("Scan history:")
    print_muted(_history_url(config))
    if final_state and (final_state.ai_status or "").lower() == "pending":
        print_muted("")
        print_muted(
            "AI recommendations are still queued on the server. "
            "Open the scan URL above to refresh when ready."
        )

    if results.overall_score is not None:
        print_muted(f"\nOverall score: {results.overall_score:.0f}")

    if results.findings:
        get_console().print(findings_table(results.findings[:25]))
        if len(results.findings) > 25:
            print_muted(f"Showing 25 of {len(results.findings)} findings. Use --json for all.")
