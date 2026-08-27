"""``devsec scan`` and ``devsec ai`` — repository scan + AI recommendation status."""

from __future__ import annotations

import time
from typing import Any

import typer

from devsec.commands.base import command, make_client
from devsec.output.console import get_console, print_muted, print_success

app = typer.Typer(
    help="Run repository scans and inspect AI recommendation progress.",
    no_args_is_help=True,
    add_completion=False,
)

ai_app = typer.Typer(help="AI recommendation status commands.", no_args_is_help=True)
app.add_typer(ai_app, name="ai")


def _frontend_url(config, scan_id: str) -> str:
    base = (config.frontend_url or "http://localhost:5174").rstrip("/")
    return f"{base}/scans/{scan_id}"


def _ai_url(config, scan_id: str) -> str:
    base = (config.frontend_url or "http://localhost:5174").rstrip("/")
    return f"{base}/scans/{scan_id}/ai"


@app.command("start")
@command
def scan_start(
    repository_url: str = typer.Argument(..., help="Git repository URL to scan."),
    branch: str = typer.Option("main", "--branch", "-b", help="Branch to scan."),
    wait_ai: bool = typer.Option(False, "--wait-ai", help="Wait for AI recommendations to finish."),
    wait_ai_timeout: int = typer.Option(300, "--wait-ai-timeout", help="Seconds to wait for AI."),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Start a repository scan (same pipeline as the Web UI)."""
    config, client = make_client()
    try:
        response = client.post(
            "/scan/start",
            json={
                "repository_url": repository_url,
                "branch": branch,
                "include_ai_explanations": True,
            },
        )
        payload = response.json()
        scan_id = str(payload.get("scan_id") or payload.get("id") or "")
        if not json:
            print_success(f"Scan started: {scan_id}")
            _poll_scan_progress(client, scan_id, config)
            if wait_ai:
                _wait_for_ai(client, scan_id, wait_ai_timeout, config)
            else:
                print_muted("")
                print_muted("Scan completed. AI recommendations are being generated in the background.")
                print_muted(f"View results: {_frontend_url(config, scan_id)}")
                print_muted(f"AI recommendations: {_ai_url(config, scan_id)}")
        return payload
    finally:
        client.close()


@app.command("status")
@command
def scan_status(
    scan_id: str = typer.Argument(..., help="Scan UUID."),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
    """Show scan lifecycle status."""
    _, client = make_client()
    try:
        response = client.get(f"/scan/status/{scan_id}")
        data = response.json()
        if not json:
            status = data.get("status") or data.get("scan_status")
            progress = data.get("progress", 0)
            get_console().print(f"Scan {scan_id}: {status} ({progress}%)")
            if data.get("current_stage"):
                get_console().print(f"  Stage: {data['current_stage']}")
        return data
    finally:
        client.close()


@ai_app.command("status")
@command
def ai_status(
    scan_id: str = typer.Argument(..., help="Scan UUID."),
    *,
    json: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
) -> dict:
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
) -> dict:
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


def _poll_scan_progress(client, scan_id: str, config) -> None:
    console = get_console()
    terminal = {"completed", "failed", "cancelled"}
    while True:
        response = client.get(f"/scan/status/{scan_id}")
        data = response.json()
        status = data.get("status") or data.get("scan_status")
        step = data.get("current_step") or data.get("current_stage") or ""
        progress = data.get("progress", 0)
        console.print(f"  [{progress:>3}%] {step or status}")
        if status in terminal:
            if status == "completed":
                print_success("Scan completed")
            break
        time.sleep(2)


def _wait_for_ai(client, scan_id: str, timeout: int, config) -> None:
    console = get_console()
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/scans/{scan_id}/ai/status")
        data = response.json()
        ai_status = data.get("ai_status")
        by_status = data.get("by_status") or {}
        completed = by_status.get("completed", 0)
        total = data.get("total_jobs", 0)
        console.print(f"  AI: {ai_status} ({completed}/{total} recommendations ready)")
        if ai_status in ("completed", "failed"):
            break
        time.sleep(3)
    print_muted(f"View results: {_frontend_url(config, scan_id)}")
