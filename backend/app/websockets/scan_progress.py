"""
WebSocket handler for real-time scan progress streaming.

Provides a WebSocket endpoint at /ws/scan/{scan_id} that:
- Streams scan progress updates in real-time
- Handles the full connection lifecycle (connect, stream, disconnect)
- Supports multiple concurrent clients per scan_id
- Gracefully handles client disconnects and server errors
- Enforces tenant isolation via JWT authentication
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

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
    # Per-scanner lifecycle events
    SCANNER_START = "scanner_start"
    SCANNER_COMPLETE = "scanner_complete"
    # Live finding stream
    FINDING_ADDED = "finding_added"
    # AI generation progress
    AI_PROGRESS = "ai_progress"
    # AI generation completed
    AI_COMPLETED = "ai_completed"
    # AI recommendation pipeline events (async, scan-independent)
    AI_ANALYSIS_STARTED = "ai.analysis.started"
    AI_FINDING_COMPLETED = "ai.finding.completed"
    AI_ANALYSIS_COMPLETED = "ai.analysis.completed"
    AI_ANALYSIS_FAILED = "ai.analysis.failed"
    # AI pipeline stage events (granular per-finding pipeline)
    AI_RAG_COMPLETED = "ai.rag.completed"
    AI_MCP_DECISION = "ai.mcp.decision"
    AI_MCP_COMPLETED = "ai.mcp.completed"
    AI_LLM_STARTED = "ai.llm.started"
    AI_LLM_COMPLETED = "ai.llm.completed"
    AI_CACHE_HIT = "ai.cache.hit"
    AI_RECOMMENDATION_UPDATED = "ai.recommendation.updated"
    # Stage transition (richer than progress_update)
    STAGE_TRANSITION = "stage_transition"
    # User-facing lifecycle events
    SCAN_STAGE = "scan_stage"
    TECHNOLOGY_DETECTED = "technology_detected"
    SCAN_CANCELLED = "scan_cancelled"
    SCAN_STATE = "scan_state"
    SCAN_STARTED = "scan_started"
    SCAN_PROGRESS = "scan_progress"
    TECHNOLOGY_SCAN_STARTED = "technology_scan_started"
    TECHNOLOGY_SCAN_COMPLETED = "technology_scan_completed"
    FINDING_DETECTED = "finding_detected"
    AI_STARTED = "ai_started"
    SCAN_COMPLETED = "scan_completed"


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
            if websocket.client_state != WebSocketState.CONNECTED:
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
        current_step: str | None = None,
        steps: list[dict[str, Any]] | None = None,
        logs: list[str] | None = None,
        detected_stack: list[str] | None = None,
        error_message: str | None = None,
        files_list: list[str] | None = None,
        files_scanned: int | None = None,
        total_files: int | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
        severity_counts: dict[str, int] | None = None,
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
            files_list: List of file paths being scanned.
            files_scanned: Number of files scanned so far.
            total_files: Total number of files to scan.
            started_at: ISO timestamp when scan started.
            completed_at: ISO timestamp when scan completed.
            severity_counts: Breakdown of findings by severity.

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
        if files_list is not None:
            data["files_list"] = files_list
        if files_scanned is not None:
            data["files_scanned"] = files_scanned
        if total_files is not None:
            data["total_files"] = total_files
        if started_at is not None:
            data["started_at"] = started_at
        if completed_at is not None:
            data["completed_at"] = completed_at
        if severity_counts is not None:
            data["severity_counts"] = severity_counts

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
        error: str | None = None,
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
            {"scan_id": scan_id, "message": message},
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

    async def broadcast_scanner_start(
        self,
        scan_id: str,
        scanner_id: str,
        scanner_name: str,
        rules_count: int = 0,
    ) -> int:
        """Broadcast that a specific scanner has started."""
        data = {
            "scan_id": scan_id,
            "scanner_id": scanner_id,
            "scanner_name": scanner_name,
            "status": "running",
            "rules_count": rules_count,
            "started_at": datetime.utcnow().isoformat(),
        }
        message = _make_message(WSMessageType.SCANNER_START, data)
        return await self._broadcast(scan_id, message)

    async def broadcast_scanner_complete(
        self,
        scan_id: str,
        scanner_id: str,
        scanner_name: str,
        status: str,
        findings_count: int = 0,
        duration_ms: int | None = None,
        error: str | None = None,
    ) -> int:
        """Broadcast that a specific scanner has completed."""
        data: dict[str, Any] = {
            "scan_id": scan_id,
            "scanner_id": scanner_id,
            "scanner_name": scanner_name,
            "status": status,
            "findings_count": findings_count,
            "completed_at": datetime.utcnow().isoformat(),
        }
        if duration_ms is not None:
            data["duration_ms"] = duration_ms
        if error:
            data["error"] = error
        message = _make_message(WSMessageType.SCANNER_COMPLETE, data)
        return await self._broadcast(scan_id, message)

    async def broadcast_ai_progress(
        self,
        scan_id: str,
        phase: str,
        message_text: str,
        progress: int = 0,
        findings_processed: int = 0,
        findings_total: int = 0,
    ) -> int:
        """Broadcast AI generation progress."""
        data = {
            "scan_id": scan_id,
            "phase": phase,
            "message": message_text,
            "progress": progress,
            "findings_processed": findings_processed,
            "findings_total": findings_total,
            "timestamp": datetime.utcnow().isoformat(),
        }
        ws_message = _make_message(WSMessageType.AI_PROGRESS, data)
        return await self._broadcast(scan_id, ws_message)

    async def broadcast_ai_completed(
        self,
        scan_id: str,
        status: str = "completed",
        suggestions_count: int = 0,
    ) -> int:
        """Broadcast that AI suggestion generation has finished."""
        data = {
            "scan_id": scan_id,
            "status": status,
            "suggestions_count": suggestions_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
        ws_message = _make_message(WSMessageType.AI_COMPLETED, data)
        return await self._broadcast(scan_id, ws_message)

    async def broadcast_ai_analysis_started(
        self,
        scan_id: str,
        findings_total: int = 0,
        findings_processed: int = 0,
    ) -> int:
        """Broadcast that the async AI recommendation pipeline has started."""
        data = {
            "scan_id": scan_id,
            "status": "processing",
            "findings_processed": findings_processed,
            "findings_total": findings_total,
            "timestamp": datetime.utcnow().isoformat(),
        }
        ws_message = _make_message(WSMessageType.AI_ANALYSIS_STARTED, data)
        return await self._broadcast(scan_id, ws_message)

    async def broadcast_ai_finding_completed(
        self,
        scan_id: str,
        findings_processed: int,
        findings_total: int,
    ) -> int:
        """Broadcast that one recommendation (finding group) was completed."""
        data = {
            "scan_id": scan_id,
            "findings_processed": findings_processed,
            "findings_total": findings_total,
            "timestamp": datetime.utcnow().isoformat(),
        }
        ws_message = _make_message(WSMessageType.AI_FINDING_COMPLETED, data)
        return await self._broadcast(scan_id, ws_message)

    async def broadcast_ai_analysis_completed(
        self,
        scan_id: str,
        stats: dict[str, Any] | None = None,
    ) -> int:
        """Broadcast that the AI recommendation pipeline finished."""
        data = {
            "scan_id": scan_id,
            "status": "completed",
            "stats": stats or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        ws_message = _make_message(WSMessageType.AI_ANALYSIS_COMPLETED, data)
        return await self._broadcast(scan_id, ws_message)

    async def broadcast_ai_analysis_failed(
        self,
        scan_id: str,
        error: str,
    ) -> int:
        """Broadcast that the AI recommendation pipeline failed."""
        data = {
            "scan_id": scan_id,
            "status": "failed",
            "error": error[:1000],
            "timestamp": datetime.utcnow().isoformat(),
        }
        ws_message = _make_message(WSMessageType.AI_ANALYSIS_FAILED, data)
        return await self._broadcast(scan_id, ws_message)

    async def broadcast_ai_rag_completed(
        self,
        scan_id: str,
        rule_id: str,
        documents_found: int,
        method: str,
    ) -> int:
        """Broadcast that RAG retrieval completed for a finding."""
        data = {
            "scan_id": scan_id,
            "stage": "rag",
            "rule_id": rule_id,
            "documents_found": documents_found,
            "method": method,
            "timestamp": datetime.utcnow().isoformat(),
        }
        ws_message = _make_message(WSMessageType.AI_RAG_COMPLETED, data)
        return await self._broadcast(scan_id, ws_message)

    async def broadcast_ai_mcp_decision(
        self,
        scan_id: str,
        rule_id: str,
        technology: str,
        required: bool,
        reason: str,
    ) -> int:
        """Broadcast the MCP decision for a finding."""
        data = {
            "scan_id": scan_id,
            "stage": "mcp_decision",
            "rule_id": rule_id,
            "technology": technology,
            "required": required,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        }
        ws_message = _make_message(WSMessageType.AI_MCP_DECISION, data)
        return await self._broadcast(scan_id, ws_message)

    async def broadcast_ai_mcp_completed(
        self,
        scan_id: str,
        rule_id: str,
        technology: str,
        status: str,
        provider: str = "",
    ) -> int:
        """Broadcast that MCP context retrieval completed for a finding."""
        data = {
            "scan_id": scan_id,
            "stage": "mcp",
            "rule_id": rule_id,
            "technology": technology,
            "status": status,
            "provider": provider,
            "timestamp": datetime.utcnow().isoformat(),
        }
        ws_message = _make_message(WSMessageType.AI_MCP_COMPLETED, data)
        return await self._broadcast(scan_id, ws_message)

    async def broadcast_ai_llm_started(
        self,
        scan_id: str,
        rule_id: str,
        technology: str | None = None,
    ) -> int:
        """Broadcast that LLM generation started for a finding."""
        data = {
            "scan_id": scan_id,
            "stage": "llm",
            "rule_id": rule_id,
            "technology": technology,
            "timestamp": datetime.utcnow().isoformat(),
        }
        ws_message = _make_message(WSMessageType.AI_LLM_STARTED, data)
        return await self._broadcast(scan_id, ws_message)

    async def broadcast_ai_llm_completed(
        self,
        scan_id: str,
        rule_id: str,
        ai_generated: bool,
        latency_ms: float | None = None,
    ) -> int:
        """Broadcast that LLM generation completed for a finding."""
        data = {
            "scan_id": scan_id,
            "stage": "llm",
            "rule_id": rule_id,
            "ai_generated": ai_generated,
            "latency_ms": latency_ms,
            "timestamp": datetime.utcnow().isoformat(),
        }
        ws_message = _make_message(WSMessageType.AI_LLM_COMPLETED, data)
        return await self._broadcast(scan_id, ws_message)

    async def broadcast_ai_cache_hit(
        self,
        scan_id: str,
        rule_id: str,
        layer: str,
    ) -> int:
        """Broadcast that a cache hit occurred (skipping RAG/MCP/LLM)."""
        data = {
            "scan_id": scan_id,
            "stage": "cache_hit",
            "rule_id": rule_id,
            "layer": layer,
            "timestamp": datetime.utcnow().isoformat(),
        }
        ws_message = _make_message(WSMessageType.AI_CACHE_HIT, data)
        return await self._broadcast(scan_id, ws_message)

    async def broadcast_ai_recommendation_updated(
        self,
        scan_id: str,
        finding_id: str,
        rule_id: str,
        status: str,
        source: str | None,
        recommendation: dict[str, Any],
    ) -> int:
        """Broadcast that a finding's AI recommendation is ready (per-finding UI update)."""
        data = {
            "event": "ai.completed",
            "scan_id": scan_id,
            "finding_id": finding_id,
            "rule_id": rule_id,
            "status": status,
            "source": source,
            "recommendation": recommendation,
            "timestamp": datetime.utcnow().isoformat(),
        }
        ws_message = _make_message(WSMessageType.AI_RECOMMENDATION_UPDATED, data)
        return await self._broadcast(scan_id, ws_message)

    async def broadcast_stage_transition(
        self,
        scan_id: str,
        stage: str,
        stage_label: str,
        progress: int,
        status: str = "running",
    ) -> int:
        """Broadcast a stage transition event with rich metadata."""
        data = {
            "scan_id": scan_id,
            "stage": stage,
            "stage_label": stage_label,
            "progress": progress,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
        message = _make_message(WSMessageType.STAGE_TRANSITION, data)
        return await self._broadcast(scan_id, message)

    async def broadcast_scan_stage(
        self,
        scan_id: str,
        stage: str,
        status: str = "running",
        message: str = "",
        progress: int | None = None,
        error_message: str | None = None,
    ) -> int:
        """Broadcast a user-facing lifecycle stage event."""
        data: dict[str, Any] = {
            "event": "scan_stage",
            "scan_id": scan_id,
            "stage": stage,
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if progress is not None:
            data["progress"] = progress
        if error_message:
            data["error_message"] = error_message
        ws_message = _make_message(WSMessageType.SCAN_STAGE, data)
        return await self._broadcast(scan_id, ws_message)

    async def broadcast_scan_progress(
        self,
        scan_id: str,
        stage: str,
        message: str,
        *,
        status: str = "running",
        progress: int | None = None,
    ) -> int:
        """Broadcast canonical scan_progress event (also emits scan_stage for compat)."""
        data: dict[str, Any] = {
            "event": "scan_progress",
            "scan_id": scan_id,
            "stage": stage,
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if progress is not None:
            data["progress"] = progress
        await self._broadcast(scan_id, _make_message(WSMessageType.SCAN_PROGRESS, data))
        return await self.broadcast_scan_stage(
            scan_id, stage, status=status, message=message, progress=progress
        )

    async def broadcast_scan_state(self, scan_id: str, state: dict[str, Any]) -> int:
        """Broadcast full persisted scan state (WebSocket reconnect / page refresh)."""
        payload = {**state, "event": "scan_state", "scan_id": scan_id}
        return await self._broadcast(scan_id, _make_message(WSMessageType.SCAN_STATE, payload))

    async def broadcast_scan_started(self, scan_id: str, message: str = "Scan started") -> int:
        data = {
            "event": "scan_started",
            "scan_id": scan_id,
            "status": "running",
            "stage": "connecting_repository",
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return await self._broadcast(scan_id, _make_message(WSMessageType.SCAN_STARTED, data))

    async def broadcast_scan_completed(
        self,
        scan_id: str,
        *,
        findings_count: int = 0,
        technologies_count: int = 0,
        message: str = "Security scan completed",
    ) -> int:
        data = {
            "event": "scan_completed",
            "scan_id": scan_id,
            "stage": "scan_completed",
            "status": "completed",
            "progress": 100,
            "message": message,
            "findings_count": findings_count,
            "technologies_count": technologies_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return await self._broadcast(scan_id, _make_message(WSMessageType.SCAN_COMPLETED, data))

    async def broadcast_technology_detected(
        self,
        scan_id: str,
        technology: str,
        *,
        tech_id: str | None = None,
        detected: bool = True,
        findings: int = 0,
        severity_counts: dict[str, int] | None = None,
    ) -> int:
        """Broadcast that a technology was detected during the scan."""
        from app.services.scan_lifecycle import format_technology_label

        tid = tech_id or technology.lower().replace(" ", "_")
        tech_obj = {
            "id": tid,
            "name": format_technology_label(tid) if tid == technology.lower().replace(" ", "_") else technology,
            "icon": tid.replace("_", "-"),
            "status": "detected" if detected else "failed",
            "findings": findings,
        }
        data = {
            "event": "technology_detected",
            "scan_id": scan_id,
            "technology": tech_obj,
            "detected": detected,
            "findings": findings,
            "severity_counts": severity_counts or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        ws_message = _make_message(WSMessageType.TECHNOLOGY_DETECTED, data)
        return await self._broadcast(scan_id, ws_message)

    async def broadcast_technology_scan_started(
        self,
        scan_id: str,
        technology: str,
        message: str,
    ) -> int:
        data = {
            "event": "technology_scan_started",
            "scan_id": scan_id,
            "technology": technology,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return await self._broadcast(scan_id, _make_message(WSMessageType.TECHNOLOGY_SCAN_STARTED, data))

    async def broadcast_technology_scan_completed(
        self,
        scan_id: str,
        technology: str,
        findings_count: int,
        *,
        status: str = "completed",
        error: str | None = None,
    ) -> int:
        data: dict[str, Any] = {
            "event": "technology_scan_completed",
            "scan_id": scan_id,
            "technology": technology,
            "findings_count": findings_count,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if error:
            data["error"] = error
        return await self._broadcast(scan_id, _make_message(WSMessageType.TECHNOLOGY_SCAN_COMPLETED, data))

    async def broadcast_finding_added(
        self,
        scan_id: str,
        finding: dict[str, Any],
        *,
        technology: str | None = None,
        total_findings: int | None = None,
    ) -> int:
        """Broadcast a newly discovered finding in real-time."""
        data = {
            "scan_id": scan_id,
            "finding": finding,
        }
        message = _make_message(WSMessageType.FINDING_ADDED, data)
        sent = await self._broadcast(scan_id, message)

        detected_data: dict[str, Any] = {
            "event": "finding_detected",
            "scan_id": scan_id,
            "finding": finding,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if technology:
            detected_data["technology"] = technology
        if total_findings is not None:
            detected_data["total_findings"] = total_findings
        await self._broadcast(scan_id, _make_message(WSMessageType.FINDING_DETECTED, detected_data))
        return sent

    async def broadcast_ai_started(self, scan_id: str, message: str, findings_total: int = 0) -> int:
        data = {
            "event": "ai_started",
            "scan_id": scan_id,
            "status": "running",
            "message": message,
            "findings_total": findings_total,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return await self._broadcast(scan_id, _make_message(WSMessageType.AI_STARTED, data))

    async def broadcast_scan_cancelled(
        self,
        scan_id: str,
        message: str = "Scan cancelled",
    ) -> int:
        """Broadcast that a scan was cancelled."""
        data = {
            "event": "scan_cancelled",
            "scan_id": scan_id,
            "status": "cancelled",
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        ws_message = _make_message(WSMessageType.SCAN_CANCELLED, data)
        return await self._broadcast(scan_id, ws_message)

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
    0. Authenticates via first WebSocket message (no URL tokens) and verifies scan ownership
    1. Accepts the connection and registers it with the manager
    2. Sends an initial snapshot of progress (if available)
    3. Keeps the connection open, receiving optional client messages
    4. Cleans up on disconnect or error

    Heartbeat: Sends ping every 15s. If no pong received within 10s, closes connection.
    """
    from app.core.websocket_auth import authenticate_scan_websocket

    # 0. Tenant isolation: authenticate and authorize
    if not await authenticate_scan_websocket(websocket, scan_id):
        return

    # 1. Connect
    connected = await scan_progress_manager.connect(websocket, scan_id)
    if not connected:
        return

    # Heartbeat state
    last_pong_time = asyncio.get_event_loop().time()
    heartbeat_interval = 15.0  # Send ping every 15s
    pong_timeout = 10.0  # Wait 10s for pong
    pong_received = asyncio.Event()

    async def _send_heartbeat():
        """Send periodic pings and detect dead connections."""
        nonlocal last_pong_time
        while True:
            try:
                await asyncio.sleep(heartbeat_interval)
                if websocket not in scan_progress_manager._active:
                    break
                ping_msg = _make_message(
                    "ping",
                    {"scan_id": scan_id, "timestamp": asyncio.get_event_loop().time()},
                )
                await websocket.send_text(ping_msg)
                # Wait for pong with timeout
                pong_received.clear()
                try:
                    await asyncio.wait_for(pong_received.wait(), timeout=pong_timeout)
                    last_pong_time = asyncio.get_event_loop().time()
                except TimeoutError:
                    logger.warning(
                        "WebSocket heartbeat timeout - no pong received",
                        scan_id=scan_id,
                    )
                    break
            except Exception:
                break

    heartbeat_task = asyncio.create_task(_send_heartbeat())

    try:
        # 2. Send authoritative persisted state snapshot (PostgreSQL is source of truth)
        try:
            from sqlalchemy import select as sa_select

            from app.db.session import get_sync_session_factory
            from app.models.finding import Finding as FindingModel
            from app.models.scan import Scan as ScanModel
            from app.services.scan_state_service import build_scan_state_snapshot_sync

            SessionLocal = get_sync_session_factory()
            sync_db = SessionLocal()
            try:
                db_scan = sync_db.execute(
                    sa_select(ScanModel).where(ScanModel.id == scan_id)
                ).scalar_one_or_none()
                if db_scan:
                    findings = sync_db.execute(
                        sa_select(FindingModel).where(FindingModel.scan_id == scan_id)
                    ).scalars().all()
                    snapshot = build_scan_state_snapshot_sync(db_scan, list(findings))
                    await scan_progress_manager.broadcast_scan_state(scan_id, snapshot)
                    # Also send directly to this client (broadcast may include others)
                    await websocket.send_text(
                        _make_message(WSMessageType.SCAN_STATE, snapshot)
                    )
            finally:
                sync_db.close()
        except Exception as e:
            logger.warning(f"Failed to send scan_state snapshot on connect: {e}")

        # Legacy: in-memory progress store fallback for clients expecting progress_update
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
                "files_list": progress.files_list if hasattr(progress, 'files_list') else [],
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
                    timeout=heartbeat_interval,
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
                        pong_received.set()
                    elif msg_type == "pong":
                        pong_received.set()
                    elif msg_type == "unsubscribe":
                        logger.info(
                            "Client unsubscribed from scan progress",
                            scan_id=scan_id,
                        )
                        break
                except json.JSONDecodeError:
                    # Ignore non-JSON messages
                    pass
            except TimeoutError:
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
        # Cancel heartbeat task
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        # 4. Clean up
        await scan_progress_manager.disconnect(websocket)
