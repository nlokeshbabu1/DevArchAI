from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import structlog
from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = structlog.get_logger(__name__)

HEARTBEAT_INTERVAL_MS = 15_000
HEARTBEAT_TIMEOUT_MS = 10_000
MAX_CONNECTIONS_PER_SCAN = 10


class CloudWebSocketManager:
    """Manages WebSocket connections for cloud scan real-time progress."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def _get_lock(self, connection_id: str) -> asyncio.Lock:
        async with self._global_lock:
            if connection_id not in self._locks:
                self._locks[connection_id] = asyncio.Lock()
            return self._locks[connection_id]

    async def connect(self, connection_id: str, websocket: WebSocket) -> bool:
        if websocket.client_state != WebSocketState.CONNECTED:
            await websocket.accept()
        lock = await self._get_lock(connection_id)
        async with lock:
            if connection_id not in self._connections:
                self._connections[connection_id] = []
            if len(self._connections[connection_id]) >= MAX_CONNECTIONS_PER_SCAN:
                await websocket.close(code=1013, reason="Too many connections")
                return False
            self._connections[connection_id].append(websocket)
        await self._send_personal(websocket, {
            "type": "connection_ack",
            "data": {"connection_id": connection_id, "timestamp": time.time()},
        })
        logger.info(
            "cloud_ws_connected",
            connection_id=connection_id,
            client_count=len(self._connections.get(connection_id, [])),
        )
        return True

    async def disconnect(self, connection_id: str, websocket: WebSocket) -> None:
        lock = await self._get_lock(connection_id)
        async with lock:
            conns = self._connections.get(connection_id, [])
            if websocket in conns:
                conns.remove(websocket)
            if not conns:
                self._connections.pop(connection_id, None)
                self._locks.pop(connection_id, None)
        logger.info("cloud_ws_disconnected", connection_id=connection_id)

    async def _send_personal(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception:
            pass

    async def broadcast(self, connection_id: str, message: dict[str, Any]) -> int:
        lock = await self._get_lock(connection_id)
        async with lock:
            conns = list(self._connections.get(connection_id, []))
        if not conns:
            return 0
        dead: list[WebSocket] = []
        sent = 0
        for ws in conns:
            try:
                await ws.send_text(json.dumps(message, default=str))
                sent += 1
            except Exception:
                dead.append(ws)
        if dead:
            async with lock:
                live = self._connections.get(connection_id, [])
                for d in dead:
                    if d in live:
                        live.remove(d)
                if not live:
                    self._connections.pop(connection_id, None)
                    self._locks.pop(connection_id, None)
        return sent

    # ── convenience broadcasters matching CloudScanEvent schema ──

    async def stage_start(self, connection_id: str, stage: str, message: str = "") -> int:
        return await self.broadcast(connection_id, {
            "type": "stage_start",
            "data": {"stage": stage, "message": message, "progress": 0, "timestamp": time.time()},
        })

    async def stage_progress(self, connection_id: str, stage: str, progress: float, message: str = "") -> int:
        return await self.broadcast(connection_id, {
            "type": "stage_progress",
            "data": {"stage": stage, "message": message, "progress": progress, "timestamp": time.time()},
        })

    async def stage_complete(self, connection_id: str, stage: str, resource_count: int = 0, finding_count: int = 0) -> int:
        return await self.broadcast(connection_id, {
            "type": "stage_complete",
            "data": {
                "stage": stage,
                "progress": 100,
                "resource_count": resource_count,
                "finding_count": finding_count,
                "timestamp": time.time(),
            },
        })

    async def finding_discovered(self, connection_id: str, finding: dict[str, Any]) -> int:
        return await self.broadcast(connection_id, {
            "type": "finding_discovered",
            "data": {"finding": finding, "timestamp": time.time()},
        })

    async def scan_complete(self, connection_id: str, summary: dict[str, Any]) -> int:
        return await self.broadcast(connection_id, {
            "type": "scan_complete",
            "data": {**summary, "timestamp": time.time()},
        })

    async def scan_failed(self, connection_id: str, error: str) -> int:
        return await self.broadcast(connection_id, {
            "type": "scan_failed",
            "data": {"error": error, "timestamp": time.time()},
        })

    def client_count(self, connection_id: str) -> int:
        return len(self._connections.get(connection_id, []))


cloud_ws_manager = CloudWebSocketManager()
