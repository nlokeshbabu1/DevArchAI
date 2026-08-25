"""``devsec scan`` - start scans and inspect progress/results."""

from __future__ import annotations

from typing import Any

import typer

from devsec.api.progress import ProgressTracker, render_progress
from devsec.api.projects import get_project
from devsec.api.scans import (
    ensure_scan_completed,
    evaluate_scan_outcome,
    get_scan_results,
    get_scan_status,
    start_scan,
)
from devsec.commands.base import command, make_client
from devsec.models.scan import ScanResultsResponse, ScanStatusResponse
from devsec.output.console import get_console, is_ci, print_error, print_muted, print_success
from devsec.output.json import emit
from devsec.output.tables import findings_table, scan_summary_table
from devsec.utils.errors import DevSecError, ExitCode, PolicyViolationError, UsageError

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
    branch: str | None = typer.Option(None, "--branch", "-b", help="Branch to scan."),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for scan completion."),
    fail_on: str = typer.Option(
        "high",
        "--fail-on",
        help="Exit 1 when findings at/above this severity exist.",
    ),
    include_ai: bool = typer.Option(
        True,
        "--include-ai/--no-ai",
        help="Request AI explanations from the backend.",
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


def _resolve_project(config, client, project_id: str | None):
    selected = (project_id or config.selected_project or "").strip()
    if not selected:
        raise UsageError(
            "No project selected.",
            hint='Run "devsec project select <id>" or pass --project <id>.',
        )
    return get_project(client, selected)


def _run_scan(
    *,
    project_id: str | None,
    branch: str | None,
    wait: bool,
    fail_on: str,
    include_ai: bool,
    json_mode: bool,
    quiet_mode: bool,
) -> dict[str, Any]:
    config, client = make_client()
    try:
        project = _resolve_project(config, client, project_id)
        start = start_scan(
            client,
            repository_url=project.url,
            repository_id=project.id,
            branch=branch or project.default_branch,
            include_ai=include_ai,
        )

        data: dict[str, Any] = {
            "scan_id": start.scan_id,
            "status": start.status,
            "repository_id": start.repository_id or project.id,
            "repository_url": start.repository_url or project.url,
            "branch": start.branch or branch or project.default_branch,
            "message": start.message,
        }

        if not json_mode and not quiet_mode:
            print_success(f"Scan started: {start.scan_id}")
            if start.message:
                print_muted(start.message)

        if not wait:
            return data

        tracker = ProgressTracker(client, start.scan_id)
        last_progress = -1

        def on_update(state) -> None:
            nonlocal last_progress
            if state.progress != last_progress or state.is_terminal:
                last_progress = state.progress
                render_progress(state)

        final_status = tracker.wait(on_update=on_update)
        ensure_scan_completed(final_status)
        results = get_scan_results(client, start.scan_id)
        passed, reason = evaluate_scan_outcome(results, fail_on=fail_on)

        data.update(
            {
                "final_status": final_status.model_dump(),
                "results": results.model_dump(),
                "passed": passed,
                "policy_reason": reason,
            }
        )

        if not json_mode:
            _render_results(results, passed=passed, reason=reason)

        if not passed and reason:
            if json_mode:
                emit(data)
                raise typer.Exit(int(ExitCode.POLICY_VIOLATION))
            raise PolicyViolationError(reason or "Policy check failed.")
        return data
    finally:
        client.close()


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
    _, client = make_client()
    try:
        results = get_scan_results(client, scan_id)
        passed, reason = evaluate_scan_outcome(results, fail_on=fail_on)
        data = {
            **results.model_dump(),
            "passed": passed,
            "policy_reason": reason,
        }
        if not json_mode:
            _render_results(results, passed=passed, reason=reason)
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
    passed: bool,
    reason: str | None,
) -> None:
    if passed:
        print_success(f"Scan passed ({results.findings_count} finding(s)).")
    else:
        print_error(reason or "Scan failed policy check.")
    if results.overall_score is not None:
        print_muted(f"Overall score: {results.overall_score:.0f}")
    if results.findings:
        get_console().print(findings_table(results.findings[:25]))
        if len(results.findings) > 25:
            print_muted(f"Showing 25 of {len(results.findings)} findings. Use --json for all.")
