"""Live scan progress via WebSocket with HTTP state polling fallback."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, urlparse, urlunparse

from devsec.api.client import ApiClient
from devsec.api.scans import get_scan_state, get_scan_status, _scan_failure_hint
from devsec.config import Config
from devsec.models.scan import ScanStateResponse, ScanStatusResponse
from devsec.output.progress_display import LifecycleProgressRenderer
from devsec.utils.errors import ScanError


@dataclass
class ProgressState:
    """Mutable progress snapshot updated by WS or polling."""

    scan_id: str
    status: str = "pending"
    stage: str | None = None
    progress: int | None = None
    current_step: str | None = None
    error_message: str | None = None
    ai_status: str | None = None
    snapshot: ScanStateResponse | None = None
    source: str = "initial"

    def apply_state(self, payload: ScanStateResponse, *, source: str) -> None:
        self.snapshot = payload
        self.status = payload.status
        self.stage = payload.stage
        self.progress = payload.progress
        self.current_step = payload.message or payload.current_operation
        self.error_message = payload.error_message
        self.ai_status = payload.ai_status
        self.source = source

    def apply_status(self, payload: ScanStatusResponse, *, source: str) -> None:
        self.status = payload.status
        self.progress = payload.progress
        self.current_step = payload.current_step
        self.error_message = payload.error_message
        self.source = source

    def apply_ws(self, msg_type: str, data: dict[str, Any]) -> None:
        self.source = "websocket"
        if msg_type in {"progress_update", "scan_progress", "scan_stage", "stage_transition"}:
            self.status = str(data.get("status", self.status))
            if data.get("progress") is not None:
                self.progress = int(data["progress"])
            self.stage = data.get("stage") or data.get("lifecycle_stage") or self.stage
            self.current_step = data.get("message") or data.get("current_step") or self.current_step
            self.error_message = data.get("error_message") or self.error_message
        elif msg_type in {"scan_complete", "scan_completed"}:
            self.status = "completed"
            self.stage = "scan_completed"
            self.progress = 100
        elif msg_type in {"scan_failed", "scan_cancelled"}:
            self.status = "failed" if msg_type == "scan_failed" else "cancelled"
            self.error_message = data.get("error_message") or self.error_message
        elif msg_type in {"ai_started", "ai.analysis.started"}:
            self.ai_status = "processing"
        elif msg_type in {
            "ai_completed",
            "ai.analysis.completed",
            "ai_analysis_completed",
        }:
            self.ai_status = "completed"
        elif msg_type in {"ai.analysis.failed", "ai_analysis_failed"}:
            self.ai_status = "failed"
        elif msg_type == "ai_progress":
            self.ai_status = "processing"
        elif msg_type == "scan_state" and isinstance(data, dict):
            try:
                self.apply_state(ScanStateResponse.model_validate(data), source="websocket")
            except Exception:
                pass

    @property
    def is_scan_terminal(self) -> bool:
        if self.snapshot and self.snapshot.is_terminal:
            return True
        return self.status.lower() in {"completed", "failed", "cancelled"}

    @property
    def is_failed(self) -> bool:
        return self.status.lower() in {"failed", "cancelled"}


def _ws_url(config: Config, scan_id: str, token: str) -> str:
    parsed = urlparse(config.api_url.rstrip("/"))
    scheme = "wss" if parsed.scheme == "https" else "ws"
    netloc = parsed.netloc
    path = f"/ws/scan/{scan_id}"
    if token.startswith(("sk-", "dk_")):
        query = f"api_key={quote(token, safe='')}"
    else:
        query = f"token={quote(token, safe='')}"
    return urlunparse((scheme, netloc, path, "", query, ""))


def _can_use_websocket(config: Config) -> bool:
    if config._env.get("DEVSEC_DISABLE_WEBSOCKET", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        return False
    return bool(config.token)


class ProgressTracker:
    """Track scan progress using WebSocket when possible, else poll REST state."""

    def __init__(
        self,
        client: ApiClient,
        scan_id: str,
        *,
        poll_interval: float = 2.0,
        timeout: float = 3600.0,
        wait_for_ai: bool = True,
        ai_timeout: float = 600.0,
    ) -> None:
        self._client = client
        self._config = client._config  # noqa: SLF001
        self._scan_id = scan_id
        self._poll_interval = poll_interval
        self._timeout = timeout
        self._wait_for_ai = wait_for_ai
        self._ai_timeout = ai_timeout
        self.state = ProgressState(scan_id=scan_id)
        self.renderer = LifecycleProgressRenderer()

    def wait(
        self,
        *,
        on_update: Callable[[ProgressState], None] | None = None,
    ) -> ScanStateResponse:
        """Block until infrastructure scan completes (and optionally AI)."""
        if _can_use_websocket(self._config):
            try:
                final = self._wait_with_websocket(on_update=on_update)
            except Exception:
                final = self._wait_with_polling(on_update=on_update)
        else:
            final = self._wait_with_polling(on_update=on_update)

        if final.status.lower() == "failed" or final.stage == "failed":
            raise ScanError(
                f"Scan {self._scan_id} failed.",
                hint=_scan_failure_hint(final.error_message),
            )
        if final.status.lower() == "cancelled":
            raise ScanError(f"Scan {self._scan_id} was cancelled.")

        if self._wait_for_ai and not final.ai_terminal:
            final = self._wait_for_ai_completion(final, on_update=on_update)
        return final

    def _emit(self, on_update: Callable[[ProgressState], None] | None) -> None:
        self.renderer.render()
        if on_update:
            on_update(self.state)

    def _apply_and_emit(
        self,
        snapshot: ScanStateResponse,
        *,
        source: str,
        on_update: Callable[[ProgressState], None] | None,
    ) -> None:
        self.state.apply_state(snapshot, source=source)
        self.renderer.apply_state(snapshot)
        self._emit(on_update)

    def _wait_with_polling(
        self,
        *,
        on_update: Callable[[ProgressState], None] | None,
    ) -> ScanStateResponse:
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            try:
                snapshot = get_scan_state(self._client, self._scan_id)
            except Exception:
                status = get_scan_status(self._client, self._scan_id)
                snapshot = ScanStateResponse(
                    scan_id=self._scan_id,
                    status=status.status,
                    progress=status.progress,
                    message=status.current_step,
                    is_terminal=status.is_terminal,
                    error_message=status.error_message,
                )
            self._apply_and_emit(snapshot, source="polling", on_update=on_update)
            if snapshot.is_terminal and snapshot.scan_complete:
                return snapshot
            if snapshot.status.lower() in {"failed", "cancelled"}:
                return snapshot
            time.sleep(self._poll_interval)
        raise TimeoutError(f"Scan {self._scan_id} did not complete within the timeout.")

    def _wait_with_websocket(
        self,
        *,
        on_update: Callable[[ProgressState], None] | None,
    ) -> ScanStateResponse:
        import asyncio

        return asyncio.run(self._async_wait(on_update=on_update))

    async def _async_wait(
        self,
        *,
        on_update: Callable[[ProgressState], None] | None,
    ) -> ScanStateResponse:
        import websockets

        token = self._config.token
        if not token:
            return self._wait_with_polling(on_update=on_update)

        ws_url = _ws_url(self._config, self._scan_id, token)
        reconnects = 0
        max_reconnects = 5
        deadline = time.monotonic() + self._timeout

        while time.monotonic() < deadline:
            try:
                async with websockets.connect(
                    ws_url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                    open_timeout=5,
                ) as websocket:
                    reconnects = 0
                    while time.monotonic() < deadline:
                        try:
                            raw = await asyncio_wait(websocket.recv(), timeout=self._poll_interval)
                        except TimeoutError:
                            snapshot = get_scan_state(self._client, self._scan_id)
                            self._apply_and_emit(snapshot, source="polling", on_update=on_update)
                            if snapshot.is_terminal and snapshot.scan_complete:
                                return snapshot
                            if snapshot.status.lower() in {"failed", "cancelled"}:
                                return snapshot
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
                        if msg_type == "scan_state":
                            try:
                                snapshot = ScanStateResponse.model_validate(data)
                                self._apply_and_emit(snapshot, source="websocket", on_update=on_update)
                                if snapshot.is_terminal and snapshot.scan_complete:
                                    return snapshot
                                if snapshot.status.lower() in {"failed", "cancelled"}:
                                    return snapshot
                                continue
                            except Exception:
                                pass

                        self.state.apply_ws(msg_type, data)
                        self.renderer.apply_ws(msg_type, data)
                        self._emit(on_update)

                        if self.state.is_failed:
                            return ScanStateResponse(
                                scan_id=self._scan_id,
                                status=self.state.status,
                                stage="failed",
                                progress=self.state.progress,
                                message=self.state.current_step,
                                error_message=self.state.error_message,
                                is_terminal=True,
                            )
                        if self.state.is_scan_terminal:
                            snapshot = get_scan_state(self._client, self._scan_id)
                            self._apply_and_emit(snapshot, source="websocket", on_update=on_update)
                            return snapshot
            except Exception:
                reconnects += 1
                if reconnects > max_reconnects:
                    break
                await asyncio_sleep(min(2**reconnects, 30))

        return self._wait_with_polling(on_update=on_update)

    def _wait_for_ai_completion(
        self,
        snapshot: ScanStateResponse,
        *,
        on_update: Callable[[ProgressState], None] | None,
    ) -> ScanStateResponse:
        deadline = time.monotonic() + self._ai_timeout
        current = snapshot
        last_status_print = 0.0
        pending_since: float | None = (
            time.monotonic() if (current.ai_status or "").lower() == "pending" else None
        )
        while time.monotonic() < deadline:
            if current.ai_terminal:
                self.renderer.apply_state(current)
                self._emit(on_update)
                return current
            ai = (current.ai_status or "").lower()
            if ai == "processing":
                pending_since = None
            elif ai == "pending":
                if pending_since is None:
                    pending_since = time.monotonic()
                elif time.monotonic() - pending_since > 45:
                    # Backend never picked up the AI job (e.g. Celery worker missing)
                    return current
            now = time.monotonic()
            if now - last_status_print >= 15:
                self.renderer.apply_state(current)
                self._emit(on_update)
                last_status_print = now
            time.sleep(self._poll_interval)
            current = get_scan_state(self._client, self._scan_id)
            self._apply_and_emit(current, source="polling", on_update=on_update)
        self.renderer.apply_state(current)
        self._emit(on_update)
        return current


async def asyncio_wait(coro: Any, *, timeout: float) -> Any:
    import asyncio

    return await asyncio.wait_for(coro, timeout=timeout)


async def asyncio_sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)


def render_progress(state: ProgressState) -> None:
    """Render progress to stderr (safe for --json mode)."""
    renderer = LifecycleProgressRenderer()
    if state.snapshot:
        renderer.apply_state(state.snapshot)
    renderer.render()
