"""``devsec scan`` — repository scan workflow (API-backed, no local engine)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import typer

from devsec.api.progress import ProgressTracker
from devsec.api.projects import resolve_or_register_by_url, resolve_project_for_command
from devsec.api.scans import (
    evaluate_scan_outcome,
    get_scan_results,
    get_scan_status,
    start_scan,
)
from devsec.commands.base import command, make_client
from devsec.models.git import GitMetadata
from devsec.models.project import Project
from devsec.models.scan import ScanResultsResponse, ScanStartResponse
from devsec.output.console import get_console, print_muted, print_success
from devsec.utils.errors import ExitCode, PolicyViolationError, UsageError
from devsec.utils.git import get_git_metadata

app = typer.Typer(
    help="Run repository scans and inspect results (backend-driven lifecycle).",
    no_args_is_help=True,
    add_completion=False,
)

ai_app = typer.Typer(help="AI recommendation status commands.", no_args_is_help=True)
app.add_typer(ai_app, name="ai")


def _frontend_url(config, scan_id: str) -> str:
    base = (config.frontend_url or "http://localhost:5174").rstrip("/")
    return f"{base}/scans/{scan_id}"


def _resolve_branch(
    branch_opt: str | None,
    project: Project | None,
    git_meta: GitMetadata | None,
) -> str | None:
    if branch_opt and branch_opt.strip():
        return branch_opt.strip()
    if project and (project.default_branch or "").strip():
        return project.default_branch.strip()
    if git_meta and git_meta.branch and git_meta.branch not in {"HEAD", ""}:
        return git_meta.branch
    return None


def _require_branch(
    branch_opt: str | None,
    project: Project | None,
    git_meta: GitMetadata | None,
) -> str | None:
    branch = _resolve_branch(branch_opt, project, git_meta)
    if branch:
        return branch
    raise UsageError(
        "Branch not specified.",
        hint=(
            'Pass --branch <name>, set a project default with '
            '"devsec project set-branch <project-id> <branch>", or scan from a '
            "git checkout with a named branch."
        ),
    )


def _resolve_scan_target(
    *,
    repo_url: str | None,
    project_id: str | None,
    path: str | None,
    config,
    client,
) -> tuple[str, str | None, Project | None, GitMetadata, bool]:
    """Return (url, repository_id, project, git_meta, use_git_branch)."""
    scan_root = Path(path or os.getcwd())
    git_meta = get_git_metadata(scan_root)
    if path and not git_meta.is_git:
        raise UsageError(
            "Not a git repository.",
            hint="Run 'devsec scan' inside a git repository, or use devsec scan --repo <url>.",
        )

    project: Project | None = None
    if repo_url and repo_url.strip():
        url = repo_url.strip()
        project = resolve_or_register_by_url(client, url)
        return url, str(project.id), project, git_meta, False

    if project_id and project_id.strip():
        project = resolve_project_for_command(
            client,
            project_id,
            selected_project=config.selected_project,
        )
        return project.url, project.id, project, git_meta, False

    if config.selected_project:
        try:
            project = resolve_project_for_command(
                client,
                None,
                selected_project=config.selected_project,
            )
            return project.url, project.id, project, git_meta, False
        except UsageError:
            pass

    if git_meta.is_git:
        url = git_meta.require_remote()
        try:
            project = resolve_or_register_by_url(client, url)
            return url, project.id, project, git_meta, True
        except Exception:
            return url, None, None, git_meta, True

    raise UsageError(
        "No project selected.",
        hint='Run "devsec project select <id>" or use devsec scan --repo <url>.',
    )


def _results_payload(
    scan_id: str,
    results: ScanResultsResponse,
    *,
    passed: bool,
    reason: str | None,
) -> dict[str, Any]:
    return {
        "scan_id": scan_id,
        "passed": passed,
        "status": results.status,
        "results": results.model_dump(mode="json"),
        "reason": reason,
    }


def _policy_exit(payload: dict[str, Any], *, json_mode: bool) -> None:
    if json_mode:
        from devsec.output.json import emit

        emit(payload)
        raise typer.Exit(int(ExitCode.POLICY_VIOLATION))
    raise PolicyViolationError(payload.get("reason") or "Scan policy check failed.")


@app.callback(invoke_without_command=True)
@command
def scan_default(
    ctx: typer.Context,
    repo: str | None = typer.Option(
        None,
        "--repo",
        help="Repository URL to scan (auto-registers as a project when needed).",
    ),
    project: str | None = typer.Option(
        None,
        "--project",
        help="Project (repository) ID or prefix.",
    ),
    branch: str | None = typer.Option(
        None,
        "--branch",
        "-b",
        help="Branch to scan (defaults to project or current git branch).",
    ),
    path: str | None = typer.Option(
        None,
        "--path",
        help="Path to a local git repository (default: current directory).",
    ),
    no_wait: bool = typer.Option(
        False,
        "--no-wait",
        help="Return after the scan is queued; do not wait for completion.",
    ),
    fail_on: str = typer.Option(
        "high",
        "--fail-on",
        help='Exit 1 when findings at or above this severity exist (use "none" to disable).',
    ),
    wait_ai: bool = typer.Option(
        False,
        "--wait-ai",
        help="After the scan completes, wait for AI recommendations to finish.",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal progress output (stderr).",
    ),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output."),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict[str, Any] | ScanStartResponse | None:
    """Scan a repository (selected project, git remote, or --repo URL)."""
    if ctx.invoked_subcommand is not None:
        return None

    from devsec.output.console import set_output_mode

    if quiet or no_color:
        set_output_mode(quiet=quiet, no_color=no_color)

    config, client = make_client()
    try:
        repository_url, repository_id, project_obj, git_meta, use_git_branch = _resolve_scan_target(
            repo_url=repo,
            project_id=project,
            path=path,
            config=config,
            client=client,
        )

        git_for_branch = git_meta if use_git_branch else None
        if no_wait:
            branch_value = _require_branch(branch, project_obj, git_for_branch)
        else:
            branch_value = _resolve_branch(branch, project_obj, git_for_branch)

        start = start_scan(
            client,
            repository_url=repository_url,
            repository_id=repository_id,
            branch=branch_value,
        )
        scan_id = start.scan_id

        if no_wait:
            if not json:
                print_success(f"Scan queued: {scan_id} (status: {start.status})")
                print_muted(f"Track progress: devsec scan status {scan_id}")
            return start.model_dump(mode="json")

        if not json:
            print_success(f"Scan started: {scan_id}")

        tracker = ProgressTracker(
            client,
            scan_id,
            wait_for_ai=wait_ai,
        )
        tracker.wait()

        results = get_scan_results(client, scan_id)
        passed, reason = evaluate_scan_outcome(results, fail_on=fail_on)
        payload = _results_payload(scan_id, results, passed=passed, reason=reason)

        if not passed:
            _policy_exit(payload, json_mode=json)

        if not json:
            print_success("Scan passed policy check.")
            print_muted(f"View results: {_frontend_url(config, scan_id)}")

        return payload
    finally:
        client.close()


@app.command("start")
@command
def scan_start_explicit(
    repository_url: str = typer.Argument(..., help="Git repository URL to scan."),
    branch: str | None = typer.Option(None, "--branch", "-b", help="Branch to scan."),
    no_wait: bool = typer.Option(False, "--no-wait", help="Do not wait for completion."),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict[str, Any] | ScanStartResponse:
    """Start a scan for an explicit repository URL."""
    config, client = make_client()
    try:
        project = resolve_or_register_by_url(client, repository_url.strip())
        start = start_scan(
            client,
            repository_url=project.url,
            repository_id=project.id,
            branch=branch,
        )
        if no_wait:
            if not json:
                print_success(f"Scan queued: {start.scan_id}")
            return start.model_dump(mode="json")
        tracker = ProgressTracker(client, start.scan_id, wait_for_ai=False)
        tracker.wait()
        return start.model_dump(mode="json")
    finally:
        client.close()


@app.command("status")
@command
def scan_status(
    scan_id: str = typer.Argument(..., help="Scan UUID."),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict[str, Any]:
    """Show scan lifecycle status."""
    _, client = make_client()
    try:
        status = get_scan_status(client, scan_id)
        data = status.model_dump(mode="json")
        if not json:
            progress = data.get("progress", 0)
            step = data.get("current_step") or data.get("status")
            get_console().print(f"Scan {scan_id}: {data.get('status')} ({progress}%)")
            if step:
                get_console().print(f"  Step: {step}")
        return data
    finally:
        client.close()


@app.command("results")
@command
def scan_results(
    scan_id: str = typer.Argument(..., help="Scan UUID."),
    fail_on: str = typer.Option(
        "high",
        "--fail-on",
        help='Exit 1 when findings at or above this severity exist (use "none" to disable).',
    ),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict[str, Any]:
    """Fetch scan results and evaluate severity policy."""
    _, client = make_client()
    try:
        results = get_scan_results(client, scan_id)
        passed, reason = evaluate_scan_outcome(results, fail_on=fail_on)
        payload = _results_payload(scan_id, results, passed=passed, reason=reason)
        if not passed:
            _policy_exit(payload, json_mode=json)
        if not json:
            get_console().print(f"Scan {scan_id}: passed policy ({fail_on})")
        return payload
    finally:
        client.close()


@ai_app.command("status")
@command
def ai_status(
    scan_id: str = typer.Argument(..., help="Scan UUID."),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict[str, Any]:
    """Show aggregate AI recommendation status for a scan."""
    config, client = make_client()
    try:
        response = client.get(f"/scans/{scan_id}/ai/status")
        data = response.json()
        if not json:
            by_status = data.get("by_status") or {}
            get_console().print(f"AI status for scan {scan_id}: {data.get('ai_status')}")
            for key, count in sorted(by_status.items()):
                get_console().print(f"  {key}: {count}")
            print_muted(f"Results: {_frontend_url(config, scan_id)}")
        return data
    finally:
        client.close()


@ai_app.command("findings")
@command
def ai_findings(
    scan_id: str = typer.Argument(..., help="Scan UUID."),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict[str, Any]:
    """List per-finding AI recommendation states."""
    _, client = make_client()
    try:
        response = client.get(f"/scans/{scan_id}/ai/findings")
        data = response.json()
        if not json:
            findings = data.get("findings") or {}
            for finding_id, info in findings.items():
                get_console().print(
                    f"  {info.get('rule_id')} ({finding_id[:8]}…): {info.get('status')}"
                )
        return data
    finally:
        client.close()
