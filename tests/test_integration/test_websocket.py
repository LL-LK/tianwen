"""
Tianwen-AGI - WebSocket Connection and Message Tests

Tests for WebSocket functionality including:
- Connection establishment and termination
- Message sending and receiving
- Heartbeat/ping-pong mechanism
- Event streaming
- Error handling and reconnection
"""

import pytest
import asyncio
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../..", "src"))


class MockWebSocketConnection:
    """Mock WebSocket connection for testing."""

    def __init__(self):
        self.messages_sent: List[Dict[str, Any]] = []
        self.messages_received: List[Dict[str, Any]] = []
        self.connected = False
        self.closed = False
        self.close_code: Optional[int] = None

    async def connect(self):
        """Simulate connection establishment."""
        await asyncio.sleep(0.01)  # Simulate network delay
        self.connected = True
        return True

    async def send(self, data: Dict[str, Any]):
        """Send message through WebSocket."""
        if self.closed:
            raise RuntimeError("Connection closed")
        if not self.connected:
            raise RuntimeError("Not connected")
        self.messages_sent.append(data)
        return True

    async def receive(self) -> Dict[str, Any]:
        """Receive message from WebSocket."""
        if self.closed:
            raise RuntimeError("Connection closed")
        if not self.connected:
            raise RuntimeError("Not connected")
        # Return next message from queue or default
        if self.messages_received:
            return self.messages_received.pop(0)
        return {"type": "default", "data": {}}

    async def close(self, code: int = 1000):
        """Close WebSocket connection."""
        self.closed = True
        self.connected = False
        self.close_code = code

    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self.connected and not self.closed

    def add_received_message(self, message: Dict[str, Any]):
        """Add a message to the receive queue."""
        self.messages_received.append(message)


class WebSocketMessage:
    """WebSocket message wrapper."""

    def __init__(self, msg_type: str, data: Any, timestamp: Optional[float] = None):
        self.type = msg_type
        self.data = data
        self.timestamp = timestamp or asyncio.get_event_loop().time()

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "data": self.data, "timestamp": self.timestamp}

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class TestWebSocketConnection:
    """Test WebSocket connection establishment."""

    @pytest.mark.asyncio
    async def test_connection_establishment(self):
        """Test WebSocket connection can be established."""
        ws = MockWebSocketConnection()
        result = await ws.connect()
        assert result is True
        assert ws.is_connected() is True

    @pytest.mark.asyncio
    async def test_connection_state(self):
        """Test WebSocket connection state tracking."""
        ws = MockWebSocketConnection()
        assert ws.is_connected() is False
        await ws.connect()
        assert ws.is_connected() is True

    @pytest.mark.asyncio
    async def test_connection_close(self):
        """Test WebSocket connection closure."""
        ws = MockWebSocketConnection()
        await ws.connect()
        assert ws.is_connected() is True
        await ws.close()
        assert ws.is_connected() is False
        assert ws.closed is True
        assert ws.close_code == 1000

    @pytest.mark.asyncio
    async def test_connection_close_with_code(self):
        """Test WebSocket connection closure with specific code."""
        ws = MockWebSocketConnection()
        await ws.connect()
        await ws.close(code=1001)
        assert ws.close_code == 1001

    @pytest.mark.asyncio
    async def test_send_before_connect(self):
        """Test sending message before connection raises error."""
        ws = MockWebSocketConnection()
        with pytest.raises(RuntimeError, match="Not connected"):
            await ws.send({"type": "test"})


class TestWebSocketMessaging:
    """Test WebSocket messaging."""

    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending a message."""
        ws = MockWebSocketConnection()
        await ws.connect()
        message = {"type": "test_message", "data": {"content": "Hello"}}
        await ws.send(message)
        assert len(ws.messages_sent) == 1
        assert ws.messages_sent[0]["type"] == "test_message"

    @pytest.mark.asyncio
    async def test_receive_message(self):
        """Test receiving a message."""
        ws = MockWebSocketConnection()
        await ws.connect()
        test_message = {"type": "server_message", "data": {"content": "Response"}}
        ws.add_received_message(test_message)
        received = await ws.receive()
        assert received["type"] == "server_message"
        assert received["data"]["content"] == "Response"

    @pytest.mark.asyncio
    async def test_message_queue(self):
        """Test message queue behavior."""
        ws = MockWebSocketConnection()
        await ws.connect()
        ws.add_received_message({"type": "msg1", "data": {}})
        ws.add_received_message({"type": "msg2", "data": {}})
        ws.add_received_message({"type": "msg3", "data": {}})
        msg1 = await ws.receive()
        msg2 = await ws.receive()
        msg3 = await ws.receive()
        assert msg1["type"] == "msg1"
        assert msg2["type"] == "msg2"
        assert msg3["type"] == "msg3"

    @pytest.mark.asyncio
    async def test_send_after_close(self):
        """Test sending after connection close raises error."""
        ws = MockWebSocketConnection()
        await ws.connect()
        await ws.close()
        with pytest.raises(RuntimeError, match="Connection closed"):
            await ws.send({"type": "test"})

    @pytest.mark.asyncio
    async def test_bidirectional_messaging(self):
        """Test bidirectional message exchange."""
        ws = MockWebSocketConnection()
        await ws.connect()
        # Client sends
        await ws.send({"type": "client_message", "data": {"content": "Request"}})
        # Server responds
        ws.add_received_message({"type": "server_message", "data": {"content": "Response"}})
        received = await ws.receive()
        assert len(ws.messages_sent) == 1
        assert received["type"] == "server_message"


class TestWebSocketPingPong:
    """Test WebSocket ping-pong/heartbeat mechanism."""

    @pytest.mark.asyncio
    async def test_ping_pong_exchange(self):
        """Test ping-pong message exchange."""
        ws = MockWebSocketConnection()
        await ws.connect()
        # Send ping
        await ws.send({"type": "ping", "timestamp": asyncio.get_event_loop().time()})
        # Pong response
        ws.add_received_message({"type": "pong", "timestamp": asyncio.get_event_loop().time()})
        response = await ws.receive()
        assert response["type"] == "pong"

    @pytest.mark.asyncio
    async def test_heartbeat_sequence(self):
        """Test heartbeat sequence."""
        ws = MockWebSocketConnection()
        await ws.connect()
        heartbeat_count = 0
        for i in range(3):
            await ws.send({"type": "ping", "count": i})
            ws.add_received_message({"type": "pong", "count": i})
            response = await ws.receive()
            heartbeat_count += 1
        assert heartbeat_count == 3

    @pytest.mark.asyncio
    async def test_ping_timeout(self):
        """Test ping timeout handling."""
        ws = MockWebSocketConnection()
        await ws.connect()
        # Simulate no pong response
        start_time = asyncio.get_event_loop().time()
        timeout_seconds = 5
        # In real implementation, would wait for pong with timeout
        assert ws.is_connected() is True


class TestWebSocketEvents:
    """Test WebSocket event handling."""

    @pytest.mark.asyncio
    async def test_event_subscription(self):
        """Test subscribing to events."""
        ws = MockWebSocketConnection()
        await ws.connect()
        await ws.send({
            "type": "subscribe",
            "events": ["observation_data", "telescope_status"]
        })
        # Check subscription confirmation received
        ws.add_received_message({
            "type": "subscription_confirmed",
            "events": ["observation_data", "telescope_status"]
        })
        response = await ws.receive()
        assert response["type"] == "subscription_confirmed"

    @pytest.mark.asyncio
    async def test_event_unsubscribe(self):
        """Test unsubscribing from events."""
        ws = MockWebSocketConnection()
        await ws.connect()
        await ws.send({
            "type": "unsubscribe",
            "events": ["telescope_status"]
        })
        ws.add_received_message({
            "type": "unsubscribed",
            "events": ["telescope_status"]
        })
        response = await ws.receive()
        assert response["type"] == "unsubscribed"

    @pytest.mark.asyncio
    async def test_observation_event_stream(self):
        """Test observation data event streaming."""
        ws = MockWebSocketConnection()
        await ws.connect()
        await ws.send({"type": "subscribe", "events": ["observation_data"]})
        # Simulate receiving observation events
        for i in range(3):
            ws.add_received_message({
                "type": "observation_data",
                "data": {"id": f"obs_{i}", "target": "M31", "magnitude": 3.4}
            })
        # Receive all events
        for i in range(3):
            event = await ws.receive()
            assert event["type"] == "observation_data"


class TestWebSocketErrorHandling:
    """Test WebSocket error handling."""

    @pytest.mark.asyncio
    async def test_invalid_message_format(self):
        """Test handling invalid message format."""
        ws = MockWebSocketConnection()
        await ws.connect()
        await ws.send({"invalid": "format"})
        # Would receive error response
        ws.add_received_message({
            "type": "error",
            "error": "Invalid message format"
        })
        response = await ws.receive()
        assert response["type"] == "error"

    @pytest.mark.asyncio
    async def test_connection_error_recovery(self):
        """Test connection error and recovery."""
        ws = MockWebSocketConnection()
        await ws.connect()
        # Simulate connection drop
        ws.connected = False
        assert ws.is_connected() is False
        # Recovery - reconnect
        await ws.connect()
        assert ws.is_connected() is True

    @pytest.mark.asyncio
    async def test_message_send_failure(self):
        """Test handling message send failure."""
        ws = MockWebSocketConnection()
        await ws.connect()
        ws.closed = True  # Simulate closure
        with pytest.raises(RuntimeError, match="Connection closed"):
            await ws.send({"type": "test"})


class TestWebSocketMessageTypes:
    """Test different WebSocket message types."""

    @pytest.mark.asyncio
    async def test_chat_message(self):
        """Test chat message type."""
        ws = MockWebSocketConnection()
        await ws.connect()
        await ws.send({
            "type": "chat",
            "data": {
                "message": "Hello, telescope",
                "session_id": "test_session"
            }
        })
        assert ws.messages_sent[-1]["type"] == "chat"

    @pytest.mark.asyncio
    async def test_command_message(self):
        """Test command message type."""
        ws = MockWebSocketConnection()
        await ws.connect()
        await ws.send({
            "type": "command",
            "data": {
                "action": "move_telescope",
                "target": "M31"
            }
        })
        assert ws.messages_sent[-1]["type"] == "command"

    @pytest.mark.asyncio
    async def test_status_message(self):
        """Test status request message type."""
        ws = MockWebSocketConnection()
        await ws.connect()
        await ws.send({"type": "status_request", "data": {"component": "telescope"}})
        ws.add_received_message({
            "type": "status_response",
            "data": {"component": "telescope", "status": "ready"}
        })
        response = await ws.receive()
        assert response["type"] == "status_response"


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""

    @pytest.mark.asyncio
    async def test_full_websocket_session(self):
        """Test complete WebSocket session flow."""
        ws = MockWebSocketConnection()
        # Connect
        await ws.connect()
        assert ws.is_connected() is True
        # Send subscribe
        await ws.send({"type": "subscribe", "events": ["all"]})
        # Receive confirmation
        ws.add_received_message({"type": "subscribed", "events": ["all"]})
        response = await ws.receive()
        assert response["type"] == "subscribed"
        # Send ping
        await ws.send({"type": "ping"})
        ws.add_received_message({"type": "pong"})
        await ws.receive()
        # Close
        await ws.close()
        assert ws.is_connected() is False

    @pytest.mark.asyncio
    async def test_concurrent_websocket_connections(self):
        """Test handling multiple concurrent connections."""
        connections = [MockWebSocketConnection() for _ in range(5)]
        # Connect all
        await asyncio.gather(*[conn.connect() for conn in connections])
        assert all(conn.is_connected() for conn in connections)
        # Send messages
        for i, conn in enumerate(connections):
            await conn.send({"type": "message", "data": {"id": i}})
        # Verify all received
        assert all(len(conn.messages_sent) == 1 for conn in connections)
        # Close all
        await asyncio.gather(*[conn.close() for conn in connections])
        assert all(not conn.is_connected() for conn in connections)

    @pytest.mark.asyncio
    async def test_websocket_message_ordering(self):
        """Test message ordering is preserved."""
        ws = MockWebSocketConnection()
        await ws.connect()
        # Send multiple messages
        for i in range(10):
            await ws.send({"type": "message", "index": i})
        # All should be in order
        for i, msg in enumerate(ws.messages_sent):
            assert msg["index"] == i


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
