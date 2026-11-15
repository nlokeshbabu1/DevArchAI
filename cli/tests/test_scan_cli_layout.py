"""CLI command registration and scan help smoke tests."""

from __future__ import annotations

from typer.testing import CliRunner

from devsec.main import app

runner = CliRunner()


def test_devsec_help_lists_scan():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "scan" in result.stdout


def test_scan_help_lists_no_wait_and_repo():
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--no-wait" in result.stdout
    assert "--repo" in result.stdout
    assert "status" in result.stdout
    assert "results" in result.stdout


def test_scan_subcommand_status_help():
    result = runner.invoke(app, ["scan", "status", "--help"])
    assert result.exit_code == 0
    assert "scan-id" in result.stdout.lower() or "Scan UUID" in result.stdout
