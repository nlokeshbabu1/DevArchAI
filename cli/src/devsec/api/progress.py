"""Live scan progress via WebSocket with HTTP polling fallback."""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse, urlunparse

from devsec.api.client import ApiClient
from devsec.api.scans import get_scan_status
from devsec.config import Config
from devsec.models.scan import ScanStatusResponse
from devsec.output.console import get_console, is_no_color, is_quiet


@dataclass
class ProgressState:
    """Mutable progress snapshot updated by WS or polling."""

    scan_id: str
    status: str = "pending"
    progress: int = 0
    current_step: str | None = None
    logs: list[str] = field(default_factory=list)
    error_message: str | None = None
    source: str = "initial"

    def apply_status(self, payload: ScanStatusResponse, *, source: str) -> None:
        self.status = payload.status
        self.progress = payload.progress
        self.current_step = payload.current_step
        if payload.logs:
            self.logs = payload.logs[-20:]
        self.error_message = payload.error_message
        self.source = source

    def apply_ws(self, msg_type: str, data: dict[str, Any]) -> None:
        self.source = "websocket"
        if msg_type in {"progress_update", "scan_complete", "scan_failed"}:
            self.status = str(data.get("status", self.status))
            self.progress = int(data.get("progress", self.progress))
            self.current_step = data.get("current_step") or self.current_step
            self.error_message = data.get("error_message") or self.error_message
        elif msg_type == "log_message":
            message = data.get("message")
            if message:
                self.logs.append(str(message))
                self.logs = self.logs[-20:]
        elif msg_type == "scan_complete":
            self.status = "completed"
            self.progress = 100
        elif msg_type == "scan_failed":
            self.status = "failed"
            self.error_message = data.get("error_message") or self.error_message

    @property
    def is_terminal(self) -> bool:
        return self.status.lower() in {"completed", "failed", "cancelled"}


def _ws_url(config: Config, scan_id: str, token: str) -> str:
    parsed = urlparse(config.api_url.rstrip("/"))
    scheme = "wss" if parsed.scheme == "https" else "ws"
    netloc = parsed.netloc
    path = f"/ws/scan/{scan_id}"
    query = f"token={token}"
    return urlunparse((scheme, netloc, path, "", query, ""))


def _can_use_websocket(config: Config) -> bool:
    """WebSocket auth accepts JWT bearer tokens, not API keys."""
    token = config.token
    if not token:
        return False
    return not token.startswith(("sk-", "dk_"))


class ProgressTracker:
    """Track scan progress using WebSocket when possible, else poll REST."""

    def __init__(
        self,
        client: ApiClient,
        scan_id: str,
        *,
        poll_interval: float = 2.0,
        ws_timeout: float = 3600.0,
    ) -> None:
        self._client = client
        self._config = client._config  # noqa: SLF001
        self._scan_id = scan_id
        self._poll_interval = poll_interval
        self._ws_timeout = ws_timeout
        self.state = ProgressState(scan_id=scan_id)

    def wait(
        self,
        *,
        on_update: Callable[[ProgressState], None] | None = None,
    ) -> ScanStatusResponse:
        """Block until the scan reaches a terminal state."""
        if _can_use_websocket(self._config):
            try:
                return self._wait_with_websocket(on_update=on_update)
            except Exception:
                pass  # noqa: S110
        return self._wait_with_polling(on_update=on_update)

    def _emit(self, on_update: Callable[[ProgressState], None] | None) -> None:
        if on_update:
            on_update(self.state)

    def _wait_with_polling(
        self,
        *,
        on_update: Callable[[ProgressState], None] | None,
    ) -> ScanStatusResponse:
        deadline = time.monotonic() + self._ws_timeout
        last_progress = -1
        while time.monotonic() < deadline:
            status = get_scan_status(self._client, self._scan_id)
            self.state.apply_status(status, source="polling")
            if status.progress != last_progress or status.is_terminal:
                last_progress = status.progress
                self._emit(on_update)
            if status.is_terminal:
                return status
            time.sleep(self._poll_interval)
        raise TimeoutError(f"Scan {self._scan_id} did not complete within the timeout.")

    def _wait_with_websocket(
        self,
        *,
        on_update: Callable[[ProgressState], None] | None,
    ) -> ScanStatusResponse:
        import asyncio

        return asyncio.run(self._async_wait(on_update=on_update))

    async def _async_wait(
        self,
        *,
        on_update: Callable[[ProgressState], None] | None,
    ) -> ScanStatusResponse:
        import websockets

        token = self._config.token
        if not token:
            return self._wait_with_polling(on_update=on_update)

        ws_url = _ws_url(self._config, self._scan_id, token)
        reconnects = 0
        max_reconnects = 5
        deadline = time.monotonic() + self._ws_timeout

        while time.monotonic() < deadline:
            try:
                async with websockets.connect(
                    ws_url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                ) as websocket:
                    reconnects = 0
                    while time.monotonic() < deadline:
                        try:
                            raw = await asyncio_wait(websocket.recv(), timeout=self._poll_interval)
                        except TimeoutError:
                            status = get_scan_status(self._client, self._scan_id)
                            self.state.apply_status(status, source="polling")
                            self._emit(on_update)
                            if status.is_terminal:
                                return status
                            continue

                        if raw == "ping":
                            await websocket.send("pong")
                            continue

                        try:
                            message = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        msg_type = message.get("type", "")
                        data = message.get("data") or {}
                        self.state.apply_ws(msg_type, data)
                        self._emit(on_update)

                        if self.state.is_terminal:
                            return ScanStatusResponse(
                                scan_id=self._scan_id,
                                status=self.state.status,
                                progress=self.state.progress,
                                current_step=self.state.current_step,
                                logs=self.state.logs,
                                error_message=self.state.error_message,
                            )
            except Exception:
                reconnects += 1
                if reconnects > max_reconnects:
                    break
                await asyncio_sleep(min(2**reconnects, 30))

        return self._wait_with_polling(on_update=on_update)


async def asyncio_wait(coro: Any, *, timeout: float) -> Any:
    import asyncio

    return await asyncio.wait_for(coro, timeout=timeout)


async def asyncio_sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)


def render_progress(state: ProgressState) -> None:
    """Render a single progress line to stderr (safe for --json mode)."""
    if is_quiet():
        return
    step = state.current_step or state.status
    line = f"[{state.progress:3d}%] {step}"
    if is_no_color():
        print(line, file=sys.stderr)
        return
    console = get_console(stderr=True)
    console.print(f"[info]{line}[/info]")
