"""
Tianwen-AGI Integration Tests - pytest fixtures and configuration
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
from dataclasses import dataclass, field

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../..", "src"))

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_api_key():
    """Mock API key for testing."""
    return "test_api_key_12345"


@pytest.fixture
def mock_session_id():
    """Mock session ID for testing."""
    return "test_session_001"


@pytest.fixture
def mock_harness_config():
    """Mock harness configuration."""
    return {
        "max_concurrent_agents": 4,
        "max_concurrent_tasks": 8,
        "retry_on_failure": True,
        "timeout_seconds": 300,
    }


@pytest.fixture
def mock_agent_config():
    """Mock agent configuration."""
    return {
        "name": "TestAgent",
        "agent_type": "researcher",
        "capabilities": ["reasoning", "web_search", "catalog_query"],
        "tools": ["web_search", "catalog_query"],
    }


@pytest.fixture
def mock_task_config():
    """Mock task configuration."""
    return {
        "name": "TestTask",
        "category": "astronomy_observation",
        "description": "Test task for integration testing",
        "difficulty": "level_2",
        "max_steps": 10,
        "tools": ["web_search"],
    }


@pytest.fixture
def mock_mcp_tool_config():
    """Mock MCP tool configuration."""
    return {
        "name": "test_mcp_tool",
        "description": "Test MCP tool",
        "category": "web_search",
        "parameters": {
            "query": {"type": "string", "required": True},
            "limit": {"type": "integer", "required": False, "default": 10}
        }
    }


@pytest.fixture
def mock_websocket_message():
    """Mock WebSocket message format."""
    return {
        "type": "test_message",
        "data": {"content": "Test content"},
        "timestamp": 1234567890.123,
    }


@pytest.fixture
def mock_api_response():
    """Mock API response format."""
    return {
        "success": True,
        "data": {"result": "test_result"},
        "message": "Operation successful",
    }


@pytest.fixture
def mock_error_response():
    """Mock error API response format."""
    return {
        "success": False,
        "error": "Test error message",
        "code": "TEST_ERROR",
    }


@pytest.fixture
def mock_health_status():
    """Mock health status response."""
    return {
        "status": "healthy",
        "version": "2.1.0",
        "uptime": 3600.0,
        "components": {
            "api": "running",
            "websocket": "running",
            "harness": "running",
            "mcp": "running",
        },
        "external_apis": {
            "minimax": "configured",
            "openai": "not_configured",
        }
    }


@pytest.fixture
def mock_observation_data():
    """Mock observation data."""
    return {
        "observation_id": "obs_001",
        "target": "M31",
        "ra": "00h 42m 44.3s",
        "dec": "+41d 16m 9s",
        "type": "galaxy",
        "magnitude": 3.4,
        "timestamp": "2026-05-19T12:00:00Z",
    }


@pytest.fixture
def mock_catalog_entry():
    """Mock catalog entry (Messier object)."""
    return {
        "id": "M31",
        "name": "Andromeda Galaxy",
        "ra": "00h 42m 44.3s",
        "dec": "+41d 16m 9s",
        "type": "galaxy",
        "magnitude": 3.4,
        "angular_size": "190' x 60'",
        "constellation": "Andromeda",
        "description": "Nearest major galaxy to the Milky Way"
    }


@pytest.fixture
def mock_benchmark_result():
    """Mock benchmark result."""
    return {
        "benchmark_id": "bench_001",
        "name": "Test Benchmark",
        "status": "completed",
        "total_tasks": 10,
        "passed_tasks": 8,
        "failed_tasks": 2,
        "pass_rate": 0.8,
        "average_score": 0.85,
        "execution_time": 120.5,
        "timestamp": "2026-05-19T12:00:00Z",
    }


@pytest.fixture
def mock_skill_info():
    """Mock skill information."""
    return {
        "skill_id": "skill_astronomy_query",
        "name": "Astronomy Query",
        "description": "Query astronomical catalogs and databases",
        "category": "astronomy",
        "parameters": {
            "target": {"type": "string", "required": True, "description": "Target object name or ID"},
            "catalog": {"type": "string", "required": False, "default": "messier", "description": "Catalog to query"},
        },
        "returns": {
            "type": "object",
            "description": "Astronomical object data including coordinates, type, and description"
        }
    }


@pytest.fixture
def mock_agent_result():
    """Mock agent execution result."""
    return {
        "agent_id": "agent_001",
        "success": True,
        "output": "Test output from agent",
        "actions": [
            {"action_type": "search", "content": "Search query"},
            {"action_type": "analyze", "content": "Analysis result"},
        ],
        "execution_time": 0.5,
        "tokens_used": 100,
    }


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.connected = True
        self._closed = False

    async def send(self, data: str):
        """Mock send message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages.append({"type": "sent", "data": data})

    async def receive(self) -> str:
        """Mock receive message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        return '{"type": "test_message", "data": {"content": "Test"}}'

    async def close(self):
        """Mock close."""
        self._closed = True
        self.connected = False

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get sent messages."""
        return self.messages


class MockHttpClient:
    """Mock HTTP client for testing external API calls."""

    def __init__(self):
        self.responses: Dict[str, Any] = {}
        self.requests: List[Dict[str, Any]] = []

    def set_response(self, url: str, response: Dict[str, Any]):
        """Set mock response for URL."""
        self.responses[url] = response

    async def get(self, url: str, **kwargs) -> MagicMock:
        """Mock GET request."""
        self.requests.append({"method": "GET", "url": url, "kwargs": kwargs})
        mock_response = MagicMock()
        if url in self.responses:
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value=self.responses[url])
            mock_response.text = str(self.responses[url])
        else:
            mock_response.status_code = 404
            mock_response.json = AsyncMock(return_value={"error": "Not found"})
        return mock_response

    async def post(self, url: str, **kwargs) -> MagicMock:
        """Mock POST request."""
        self.requests.append({"method": "POST", "url": url, "kwargs": kwargs})
        mock_response = MagicMock()
        if url in self.responses:
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value=self.responses[url])
        else:
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value={"status": "ok"})
        return mock_response

    async def close(self):
        """Mock close."""
        pass


@pytest.fixture
def mock_http_client():
    """Mock HTTP client fixture."""
    return MockHttpClient()


class AsyncIteratorMock:
    """Mock async iterator for streaming responses."""

    def __init__(self, items: List[Any]):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


@pytest.fixture
def async_iterator_mock():
    """Fixture for async iterator mock."""
    return AsyncIteratorMock


# Auto-use fixtures for common test setup
@pytest.fixture(autouse=True)
def reset_module_state():
    """Reset module state before each test."""
    yield
    # Cleanup after test if needed
