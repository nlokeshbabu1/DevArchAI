"""Unit tests for the WebSocket scan progress manager."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from fastapi import WebSocket


class TestWSMessageType:
    """Tests for WSMessageType constants."""

    def test_all_message_types_defined(self):
        """All required WebSocket message types are defined."""
        from app.websockets.scan_progress import WSMessageType
        assert WSMessageType.PROGRESS_UPDATE == "progress_update"
        assert WSMessageType.STEP_UPDATE == "step_update"
        assert WSMessageType.LOG_MESSAGE == "log_message"
        assert WSMessageType.SCAN_COMPLETE == "scan_complete"
        assert WSMessageType.SCAN_FAILED == "scan_failed"
        assert WSMessageType.STACK_DETECTED == "stack_detected"
        assert WSMessageType.CONNECTION_ACK == "connection_ack"
        assert WSMessageType.ERROR == "error"
        assert WSMessageType.SCANNER_START == "scanner_start"
        assert WSMessageType.SCANNER_COMPLETE == "scanner_complete"
        assert WSMessageType.FINDING_ADDED == "finding_added"
        assert WSMessageType.AI_PROGRESS == "ai_progress"
        assert WSMessageType.AI_COMPLETED == "ai_completed"

    def test_ai_pipeline_message_types(self):
        """All AI pipeline WebSocket message types are defined."""
        from app.websockets.scan_progress import WSMessageType
        assert WSMessageType.AI_ANALYSIS_STARTED == "ai.analysis.started"
        assert WSMessageType.AI_FINDING_COMPLETED == "ai.finding.completed"
        assert WSMessageType.AI_ANALYSIS_COMPLETED == "ai.analysis.completed"
        assert WSMessageType.AI_ANALYSIS_FAILED == "ai.analysis.failed"
        assert WSMessageType.AI_RAG_COMPLETED == "ai.rag.completed"
        assert WSMessageType.AI_MCP_DECISION == "ai.mcp.decision"
        assert WSMessageType.AI_MCP_COMPLETED == "ai.mcp.completed"
        assert WSMessageType.AI_LLM_STARTED == "ai.llm.started"
        assert WSMessageType.AI_LLM_COMPLETED == "ai.llm.completed"
        assert WSMessageType.AI_CACHE_HIT == "ai.cache.hit"
        assert WSMessageType.STAGE_TRANSITION == "stage_transition"


class TestMakeMessage:
    """Tests for the _make_message helper."""

    def test_make_message_json_format(self):
        """_make_message produces valid JSON with type and data fields."""
        from app.websockets.scan_progress import _make_message
        msg = _make_message("test_type", {"key": "value"})
        parsed = json.loads(msg)
        assert parsed["type"] == "test_type"
        assert parsed["data"]["key"] == "value"

    def test_make_message_empty_data(self):
        """_make_message works with empty data dict."""
        from app.websockets.scan_progress import _make_message
        msg = _make_message("test", {})
        parsed = json.loads(msg)
        assert parsed["type"] == "test"
        assert parsed["data"] == {}


class TestScanProgressWebSocketManager:
    """Tests for ScanProgressWebSocketManager."""

    @pytest.fixture
    def manager(self):
        """Provide a fresh WebSocket manager."""
        from app.websockets.scan_progress import ScanProgressWebSocketManager
        return ScanProgressWebSocketManager()

    def _mock_websocket(self, scan_id: str = "scan-123") -> MagicMock:
        """Create a mock WebSocket."""
        from starlette.websockets import WebSocketState

        ws = AsyncMock(spec=WebSocket)
        ws.client_state = WebSocketState.CONNECTING
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_success(self, manager):
        """Successful connection adds to connections dict."""
        ws = self._mock_websocket()
        result = await manager.connect(ws, "scan-123")
        assert result is True
        count = await manager.get_connection_count("scan-123")
        assert count == 1

    @pytest.mark.asyncio
    async def test_connect_idempotent_for_same_socket(self, manager):
        """Registering the same WebSocket twice does not duplicate subscribers."""
        ws = self._mock_websocket()
        assert await manager.connect(ws, "scan-123") is True
        assert await manager.connect(ws, "scan-123") is True
        assert await manager.get_connection_count("scan-123") == 1

    @pytest.mark.asyncio
    async def test_connect_accept_failure(self, manager):
        """WebSocket accept failure returns False."""
        ws = self._mock_websocket()
        ws.accept.side_effect = Exception("accept failed")
        result = await manager.connect(ws, "scan-123")
        assert result is False

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, manager):
        """disconnect removes the WebSocket from connections."""
        ws = self._mock_websocket()
        await manager.connect(ws, "scan-123")
        await manager.disconnect(ws)
        count = await manager.get_connection_count("scan-123")
        assert count == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_clients(self, manager):
        """Broadcast reaches all connected clients for a scan."""
        ws1 = self._mock_websocket()
        ws2 = self._mock_websocket()
        await manager.connect(ws1, "scan-123")
        await manager.connect(ws2, "scan-123")
        count = await manager.broadcast_progress("scan-123", 50, "running", "scanning")
        assert count == 2
        ws1.send_text.assert_awaited()
        ws2.send_text.assert_awaited()

    @pytest.mark.asyncio
    async def test_broadcast_nonexistent_scan(self, manager):
        """Broadcast to non-existent scan returns 0."""
        count = await manager.broadcast_progress("no-such-scan", 50, "running")
        assert count == 0

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self, manager):
        """Dead connections (send failure) are removed on broadcast."""
        ws_good = self._mock_websocket()
        ws_dead = self._mock_websocket()
        ws_dead.send_text.side_effect = Exception("connection closed")
        await manager.connect(ws_good, "scan-123")
        await manager.connect(ws_dead, "scan-123")
        count = await manager.broadcast_progress("scan-123", 50, "running")
        # Only the good connection survives
        assert count == 1

    @pytest.mark.asyncio
    async def test_broadcast_finding_added(self, manager):
        """broadcast_finding_added sends finding data."""
        ws = self._mock_websocket()
        await manager.connect(ws, "scan-123")
        finding = {"id": "f1", "severity": "high", "rule_id": "TF-001"}
        count = await manager.broadcast_finding_added("scan-123", finding)
        assert count >= 1

    @pytest.mark.asyncio
    async def test_broadcast_ai_rag_completed(self, manager):
        """broadcast_ai_rag_completed sends correct data."""
        ws = self._mock_websocket()
        await manager.connect(ws, "scan-123")
        count = await manager.broadcast_ai_rag_completed("scan-123", "TF-001", 3, "keyword")
        assert count == 1

    @pytest.mark.asyncio
    async def test_broadcast_ai_mcp_decision(self, manager):
        """broadcast_ai_mcp_decision sends MCP decision data."""
        ws = self._mock_websocket()
        await manager.connect(ws, "scan-123")
        count = await manager.broadcast_ai_mcp_decision("scan-123", "TF-001", "aws", True, "live context")
        assert count == 1

    @pytest.mark.asyncio
    async def test_broadcast_ai_llm_started(self, manager):
        """broadcast_ai_llm_started sends correct data."""
        ws = self._mock_websocket()
        await manager.connect(ws, "scan-123")
        count = await manager.broadcast_ai_llm_started("scan-123", "TF-001", "terraform")
        assert count == 1

    @pytest.mark.asyncio
    async def test_broadcast_ai_llm_completed(self, manager):
        """broadcast_ai_llm_completed sends correct data."""
        ws = self._mock_websocket()
        await manager.connect(ws, "scan-123")
        count = await manager.broadcast_ai_llm_completed("scan-123", "TF-001", True, 150.5)
        assert count == 1

    @pytest.mark.asyncio
    async def test_broadcast_ai_cache_hit(self, manager):
        """broadcast_ai_cache_hit sends correct data."""
        ws = self._mock_websocket()
        await manager.connect(ws, "scan-123")
        count = await manager.broadcast_ai_cache_hit("scan-123", "TF-001", "redis")
        assert count == 1

    @pytest.mark.asyncio
    async def test_broadcast_stage_transition(self, manager):
        """broadcast_stage_transition sends correct data."""
        ws = self._mock_websocket()
        await manager.connect(ws, "scan-123")
        count = await manager.broadcast_stage_transition("scan-123", "scanning", "Scanning", 30)
        assert count == 1

    @pytest.mark.asyncio
    async def test_broadcast_scanner_start(self, manager):
        """broadcast_scanner_start sends correct data."""
        ws = self._mock_websocket()
        await manager.connect(ws, "scan-123")
        count = await manager.broadcast_scanner_start("scan-123", "trivy", "Trivy", 5)
        assert count == 1

    @pytest.mark.asyncio
    async def test_broadcast_scanner_complete(self, manager):
        """broadcast_scanner_complete sends correct data."""
        ws = self._mock_websocket()
        await manager.connect(ws, "scan-123")
        count = await manager.broadcast_scanner_complete("scan-123", "trivy", "Trivy", "completed", 3, 1500)
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_connection_count_empty(self, manager):
        """get_connection_count returns 0 for unknown scan."""
        count = await manager.get_connection_count("unknown-scan")
        assert count == 0


class TestAuthenticateWebsocket:
    """Tests for scan WebSocket authentication (core.websocket_auth)."""

    @pytest.mark.asyncio
    async def test_no_token_close_code_4001(self):
        """Missing auth message => close(4001)."""
        from app.core.websocket_auth import (
            WS_CLOSE_AUTH_REQUIRED,
            receive_websocket_credentials,
        )

        ws = AsyncMock(spec=WebSocket)
        ws.query_params = {}
        ws.headers = {}
        ws.url.path = "/ws/scan/scan-123"
        ws.accept = AsyncMock()
        ws.close = AsyncMock()

        with patch("app.core.websocket_auth.asyncio.wait_for", side_effect=TimeoutError):
            creds = await receive_websocket_credentials(ws)

        assert creds is None
        ws.close.assert_awaited()
        assert ws.close.await_args.kwargs.get("code") == WS_CLOSE_AUTH_REQUIRED
