"""Shared command plumbing: error handling, JSON mode, client factory."""

from __future__ import annotations

import functools
import traceback
from collections.abc import Callable
from typing import Any

import typer

from devsec.api.client import ApiClient
from devsec.config import Config
from devsec.output.console import error_line
from devsec.output.json import emit, emit_error
from devsec.utils.errors import ApiError, DevSecError, ExitCode, error_detail

# Process-wide debug flag set by the root Typer callback (``--debug``).
_DEBUG = False


def set_debug(enabled: bool) -> None:
    """Enable or disable debug mode for this process."""
    global _DEBUG
    _DEBUG = bool(enabled)


def is_debug() -> bool:
    """Return whether ``--debug`` is active."""
    return _DEBUG


def command(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a Typer command body with centralized error handling.

    - ``--json`` commands emit their result via :func:`emit` when the body
      returns a dict.
    - Expected :class:`DevSecError` failures print a friendly message (or a
      JSON error payload in ``--json`` mode) and exit with the error's stable
      exit code.
    - Unexpected exceptions are reported as bugs and exit with ``USAGE``.
    - Stack traces are never shown unless ``--debug`` is set.
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        json_mode = bool(kwargs.get("json"))
        try:
            result = fn(*args, **kwargs)
            if json_mode and result is not None:
                emit(result)
            return None
        except typer.Exit:
            raise
        except DevSecError as exc:
            _report_error(exc, json_mode)
            raise typer.Exit(int(exc.exit_code)) from None
        except Exception as exc:  # noqa: BLE001 - last-resort boundary
            _report_unexpected(exc, json_mode)
            raise typer.Exit(int(ExitCode.USAGE)) from None

    return wrapper


def make_client(config: Config | None = None) -> tuple[Config, ApiClient]:
    """Build a resolved config and API client for a command."""
    resolved = config or Config()
    return resolved, ApiClient(resolved)


def _report_error(exc: DevSecError, json_mode: bool) -> None:
    if json_mode:
        emit_error(error_detail(exc))
        return
    error_line(f"[error]Error:[/error] {exc.message}")
    if exc.hint:
        error_line(f"Hint: {exc.hint}")
    if isinstance(exc, ApiError) and exc.request_id:
        error_line(f"Request ID: {exc.request_id}")
    if is_debug():
        error_line(traceback.format_exc())


def _report_unexpected(exc: BaseException, json_mode: bool) -> None:
    if json_mode:
        payload = error_detail(exc)
        if is_debug():
            payload["traceback"] = traceback.format_exc()
        emit_error(payload)
        return
    error_line(f"[error]Unexpected error:[/error] {exc}")
    if is_debug():
        error_line(traceback.format_exc())
    else:
        error_line("This looks like a bug in devsec - please report it.")
        error_line("Re-run with --debug for a full traceback.")
