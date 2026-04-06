"""
WebSocket handler for real-time scan progress streaming.

Provides a WebSocket endpoint at /ws/scan/{scan_id} that:
- Streams scan progress updates in real-time
- Handles the full connection lifecycle (connect, stream, disconnect)
- Supports multiple concurrent clients per scan_id
- Gracefully handles client disconnects and server errors
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any, Optional

import structlog
from fastapi import WebSocket, WebSocketDisconnect

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Message types that can be sent over the WebSocket
# ---------------------------------------------------------------------------

class WSMessageType:
    """Standard message types for scan progress WebSocket."""

    PROGRESS_UPDATE = "progress_update"
    STEP_UPDATE = "step_update"
    LOG_MESSAGE = "log_message"
    SCAN_COMPLETE = "scan_complete"
    SCAN_FAILED = "scan_failed"
    STACK_DETECTED = "stack_detected"
    CONNECTION_ACK = "connection_ack"
    ERROR = "error"


def _make_message(
    msg_type: str,
    data: dict[str, Any],
) -> str:
    """
    Build a JSON-encoded WebSocket message.

    Args:
        msg_type: One of the WSMessageType constants.
        data: The message payload.

    Returns:
        A JSON string ready for WebSocket transmission.
    """
    return json.dumps({
        "type": msg_type,
        "data": data,
    }, default=str)


# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------

class ScanProgressWebSocketManager:
    """
    Manages WebSocket connections for scan progress streaming.

    Supports multiple concurrent connections per scan_id.  When progress
    is broadcast for a scan_id, every connected client receives the update.
    """

    def __init__(self) -> None:
        # scan_id -> list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)
        # Track which connections are active for safe cleanup
        self._active: dict[WebSocket, str] = {}  # websocket -> scan_id
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self, websocket: WebSocket, scan_id: str) -> bool:
        """
        Accept a new WebSocket connection and register it.

        Args:
            websocket: The FastAPI WebSocket instance.
            scan_id: The scan identifier this client wants to follow.

        Returns:
            True if the connection was accepted successfully.
        """
        try:
            await websocket.accept()
            async with self._lock:
                self._connections[scan_id].append(websocket)
                self._active[websocket] = scan_id

            # Send acknowledgment
            ack = _make_message(
                WSMessageType.CONNECTION_ACK,
                {
                    "scan_id": scan_id,
                    "message": "Connected to scan progress stream",
                },
            )
            await websocket.send_text(ack)

            logger.info(
                "WebSocket client connected",
                scan_id=scan_id,
                total_clients=len(self._connections[scan_id]),
            )
            return True

        except Exception as exc:
            logger.error(
                "Failed to accept WebSocket connection",
                scan_id=scan_id,
                error=str(exc),
            )
            return False

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection from the manager.

        Args:
            websocket: The WebSocket to remove.
        """
        async with self._lock:
            scan_id = self._active.pop(websocket, None)
            if scan_id and websocket in self._connections[scan_id]:
                self._connections[scan_id].remove(websocket)
                # Clean up empty lists
                if not self._connections[scan_id]:
                    del self._connections[scan_id]

        logger.info(
            "WebSocket client disconnected",
            scan_id=scan_id,
        )

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------

    async def broadcast_progress(
        self,
        scan_id: str,
        progress: int,
        status: str,
        current_step: Optional[str] = None,
        steps: Optional[list[dict[str, Any]]] = None,
        logs: Optional[list[str]] = None,
        detected_stack: Optional[list[str]] = None,
        error_message: Optional[str] = None,
    ) -> int:
        """
        Broadcast a progress update to all clients watching a scan.

        Args:
            scan_id: The scan identifier.
            progress: Overall progress percentage (0-100).
            status: Current scan status (pending, running, completed, failed).
            current_step: Name of the currently executing step.
            steps: List of step status dictionaries.
            logs: Recent log messages.
            detected_stack: Detected technology stack.
            error_message: Error message if the scan failed.

        Returns:
            The number of clients the message was sent to.
        """
        data: dict[str, Any] = {
            "scan_id": scan_id,
            "progress": progress,
            "status": status,
        }
        if current_step is not None:
            data["current_step"] = current_step
        if steps is not None:
            data["steps"] = steps
        if logs is not None:
            data["logs"] = logs
        if detected_stack is not None:
            data["detected_stack"] = detected_stack
        if error_message is not None:
            data["error_message"] = error_message

        # Determine message type based on status
        if status == "completed":
            msg_type = WSMessageType.SCAN_COMPLETE
        elif status == "failed":
            msg_type = WSMessageType.SCAN_FAILED
        else:
            msg_type = WSMessageType.PROGRESS_UPDATE

        message = _make_message(msg_type, data)
        return await self._broadcast(scan_id, message)

    async def broadcast_step_update(
        self,
        scan_id: str,
        step_name: str,
        step_status: str,
        step_progress: int = 0,
        error: Optional[str] = None,
    ) -> int:
        """
        Broadcast an individual step status update.

        Args:
            scan_id: The scan identifier.
            step_name: Name of the step.
            step_status: Step status (pending, running, completed, failed).
            step_progress: Step progress percentage (0-100).
            error: Error message if the step failed.

        Returns:
            Number of clients the message was sent to.
        """
        data = {
            "scan_id": scan_id,
            "step_name": step_name,
            "step_status": step_status,
            "step_progress": step_progress,
        }
        if error:
            data["error"] = error

        message = _make_message(WSMessageType.STEP_UPDATE, data)
        return await self._broadcast(scan_id, message)

    async def broadcast_log(
        self,
        scan_id: str,
        message: str,
    ) -> int:
        """
        Broadcast a single log line to all connected clients.

        Args:
            scan_id: The scan identifier.
            message: The log message.

        Returns:
            Number of clients the message was sent to.
        """
        ws_message = _make_message(
            WSMessageType.LOG_MESSAGE,
            {"scan_id": scan_id, "log": message},
        )
        return await self._broadcast(scan_id, ws_message)

    async def broadcast_stack_detected(
        self,
        scan_id: str,
        stack: list[str],
    ) -> int:
        """
        Broadcast detected technology stack to all connected clients.

        Args:
            scan_id: The scan identifier.
            stack: List of detected technologies.

        Returns:
            Number of clients the message was sent to.
        """
        ws_message = _make_message(
            WSMessageType.STACK_DETECTED,
            {"scan_id": scan_id, "stack": stack},
        )
        return await self._broadcast(scan_id, ws_message)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _broadcast(self, scan_id: str, message: str) -> int:
        """
        Send a message to all active connections for a scan_id.

        Removes any dead connections encountered during broadcast.

        Args:
            scan_id: The scan identifier.
            message: The JSON-encoded message string.

        Returns:
            Number of clients the message was successfully sent to.
        """
        async with self._lock:
            clients = list(self._connections.get(scan_id, []))

        if not clients:
            return 0

        sent_count = 0
        dead_connections: list[WebSocket] = []

        for ws in clients:
            try:
                await ws.send_text(message)
                sent_count += 1
            except Exception as exc:
                logger.warning(
                    "Failed to send WebSocket message -- removing connection",
                    scan_id=scan_id,
                    error=str(exc),
                )
                dead_connections.append(ws)

        # Clean up dead connections
        if dead_connections:
            async with self._lock:
                for ws in dead_connections:
                    if ws in self._active:
                        del self._active[ws]
                    if ws in self._connections.get(scan_id, []):
                        self._connections[scan_id].remove(ws)
                if not self._connections.get(scan_id):
                    self._connections.pop(scan_id, None)

        return sent_count

    async def get_connection_count(self, scan_id: str) -> int:
        """Return the number of active connections for a scan."""
        async with self._lock:
            return len(self._connections.get(scan_id, []))


# ---------------------------------------------------------------------------
# FastAPI WebSocket endpoint
# ---------------------------------------------------------------------------

# Global manager instance
scan_progress_manager = ScanProgressWebSocketManager()


async def scan_progress_websocket(
    websocket: WebSocket,
    scan_id: str,
) -> None:
    """
    WebSocket endpoint handler for scan progress streaming.

    Usage in FastAPI router:

        from app.websockets.scan_progress import scan_progress_websocket

        @router.websocket("/ws/scan/{scan_id}")
        async def ws_scan(websocket: WebSocket, scan_id: str):
            await scan_progress_websocket(websocket, scan_id)

    The handler manages the full connection lifecycle:
    1. Accepts the connection and registers it with the manager
    2. Sends an initial snapshot of progress (if available)
    3. Keeps the connection open, receiving optional client messages
    4. Cleans up on disconnect or error
    """
    # 1. Connect
    connected = await scan_progress_manager.connect(websocket, scan_id)
    if not connected:
        return

    try:
        # 2. Send initial progress snapshot from the in-memory store
        from app.services.scan_progress_store import scan_progress_store

        progress = await scan_progress_store.get_progress(scan_id)
        if progress:
            initial_data = {
                "scan_id": progress.scan_id,
                "progress": progress.progress,
                "status": progress.status,
                "current_step": progress.current_step,
                "steps": [
                    {
                        "name": s.name,
                        "status": s.status.value if hasattr(s.status, "value") else str(s.status),
                        "progress": s.progress,
                        "error": s.error,
                    }
                    for s in progress.steps
                ],
                "detected_stack": progress.detected_stack,
                "logs": progress.logs[-20:],  # Last 20 log entries
            }
            message = _make_message(WSMessageType.PROGRESS_UPDATE, initial_data)
            await websocket.send_text(message)

        # 3. Keep connection alive -- listen for optional client messages
        #    (e.g. ping/pong, unsubscribe, etc.)
        while True:
            # Wait for a message from the client with a timeout
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0,
                )
                # Handle client messages (e.g. ping, unsubscribe)
                try:
                    client_msg = json.loads(data)
                    msg_type = client_msg.get("type", "")
                    if msg_type == "ping":
                        pong = _make_message(
                            "pong",
                            {"scan_id": scan_id, "timestamp": str(asyncio.get_event_loop().time())},
                        )
                        await websocket.send_text(pong)
                    elif msg_type == "unsubscribe":
                        logger.info(
                            "Client unsubscribed from scan progress",
                            scan_id=scan_id,
                        )
                        break
                except json.JSONDecodeError:
                    # Ignore non-JSON messages
                    pass
            except asyncio.TimeoutError:
                # No client message received -- continue listening
                # Check if the connection is still active
                if websocket not in scan_progress_manager._active:
                    break
                continue

    except WebSocketDisconnect:
        logger.info(
            "WebSocket client disconnected normally",
            scan_id=scan_id,
        )
    except Exception as exc:
        logger.error(
            "WebSocket connection error",
            scan_id=scan_id,
            error=str(exc),
        )
        # Try to send an error message before closing
        try:
            error_msg = _make_message(
                WSMessageType.ERROR,
                {"scan_id": scan_id, "error": str(exc)},
            )
            await websocket.send_text(error_msg)
        except Exception:
            pass
    finally:
        # 4. Clean up
        await scan_progress_manager.disconnect(websocket)
