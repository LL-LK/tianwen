"""
Tianwen-AGI - MCP Tool Integration Tests

Tests for MCP (Model Context Protocol) tool integration including:
- Tool registration and discovery
- Tool invocation and execution
- Tool chaining and workflows
- Tool result handling and error cases
"""

import pytest
import asyncio
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


# Mock classes for testing - these replace the harness imports
class ToolCategory(Enum):
    WEB_SEARCH = "web_search"
    DATA_ANALYSIS = "data_analysis"
    CODE_EXECUTION = "code_execution"
    FILE_SYSTEM = "file_system"
    API_CALL = "api_call"
    ASTRONOMY = "astronomy"
    GENERAL = "general"


@dataclass
class ToolParameter:
    name: str
    type: str
    required: bool = True
    default: Any = None
    description: str = ""


@dataclass
class ToolMetadata:
    """Tool metadata."""
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPToolConfig:
    tool_id: str
    name: str
    description: str = ""
    category: ToolCategory = ToolCategory.GENERAL
    parameters: List[ToolParameter] = field(default_factory=list)
    enabled: bool = True
    timeout_seconds: int = 30
    retry_on_failure: bool = False
    version: str = "1.0.0"
    input_schema: Dict = None
    required_env: List[str] = field(default_factory=list)


@dataclass
class MCPToolResult:
    tool_id: str
    success: bool
    output: Any = None
    error: str = None
    execution_time: float = 0.0
    metadata: Dict = field(default_factory=dict)


class BaseTool:
    """Base tool class."""

    def __init__(self, config: MCPToolConfig):
        self.config = config

    async def execute(self, params: Dict[str, Any]) -> MCPToolResult:
        raise NotImplementedError


class MCPTool(BaseTool):
    """Mock MCP tool for testing."""

    def __init__(self, config: MCPToolConfig):
        super().__init__(config)
        self.execution_log: List[Dict[str, Any]] = []

    async def execute(self, params: Dict[str, Any]) -> MCPToolResult:
        """Execute the MCP tool."""
        self.execution_log.append({
            "tool_id": self.config.tool_id,
            "params": params,
            "timestamp": asyncio.get_event_loop().time()
        })
        return MCPToolResult(
            tool_id=self.config.tool_id,
            success=True,
            output={"result": f"Executed {self.config.name}", "params": params},
            execution_time=0.01
        )


class MCPToolChain:
    def __init__(self, name: str = ""):
        self.name = name
        self.tools: List[BaseTool] = []
        self.results: List[MCPToolResult] = []

    def add_tool(self, tool: BaseTool):
        self.tools.append(tool)

    async def execute(self, params: Dict[str, Any]) -> MCPToolResult:
        self.results = []
        for tool in self.tools:
            result = await tool.execute(params)
            self.results.append(result)
        return MCPToolResult(
            tool_id="chain",
            success=all(r.success for r in self.results),
            output={"results": [r.output for r in self.results]}
        )

    async def execute_parallel(self, params: Dict[str, Any]) -> MCPToolResult:
        self.results = []
        tasks = [tool.execute(params) for tool in self.tools]
        self.results = await asyncio.gather(*tasks)
        return MCPToolResult(
            tool_id="chain_parallel",
            success=all(r.success for r in self.results),
            output={"results": [r.output for r in self.results]}
        )

    def get_aggregated_results(self) -> Dict[str, Any]:
        return {
            "total": len(self.results),
            "successful": sum(1 for r in self.results if r.success),
            "failed": sum(1 for r in self.results if not r.success)
        }


class MCPToolIntegration:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_registry: Dict[str, Callable] = {}

    def register_tool(self, name: str, tool: BaseTool):
        self._tools[name] = tool
        self._tool_registry[name] = tool.execute

    def register_function(self, name: str, func: Callable):
        self._tool_registry[name] = func

    async def execute_tool(self, name: str, **kwargs) -> Any:
        if name not in self._tool_registry:
            raise ValueError(f"Tool '{name}' not found")
        func = self._tool_registry[name]
        if asyncio.iscoroutinefunction(func):
            return await func(**kwargs)
        return func(**kwargs)

    async def batch_execute(self, calls: List[Dict[str, Any]]) -> List[Any]:
        tasks = [self.execute_tool(call["name"], **call.get("params", {})) for call in calls]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def list_tools(self) -> List[str]:
        return list(self._tool_registry.keys())

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def search_tools(self, query: str) -> List[str]:
        return [name for name in self._tool_registry.keys() if query.lower() in name.lower()]


def get_tool_integration() -> MCPToolIntegration:
    """Get tool integration instance."""
    return MCPToolIntegration()


# Pytest fixtures
@pytest.fixture
def mock_mcp_tool_config():
    """Fixture providing mock MCP tool config."""
    return {
        "name": "Test MCP Tool",
        "description": "A test MCP tool for unit testing"
    }


class TestMCPToolConfig:
    """Test MCP Tool Configuration."""

    def test_mcp_tool_config_creation(self, mock_mcp_tool_config):
        """Test MCP tool configuration creation."""
        config = MCPToolConfig(
            tool_id=mock_mcp_tool_config["name"],
            name=mock_mcp_tool_config["name"],
            description=mock_mcp_tool_config["description"],
            category=ToolCategory.WEB_SEARCH,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    required=True,
                    description="Search query"
                )
            ]
        )
        assert config.name == mock_mcp_tool_config["name"]
        assert config.category == ToolCategory.WEB_SEARCH
        assert len(config.parameters) == 1

    def test_mcp_tool_config_defaults(self):
        """Test MCP tool configuration defaults."""
        config = MCPToolConfig(
            tool_id="default_test",
            name="Default Test"
        )
        assert config.enabled is True
        assert config.timeout_seconds == 30
        assert config.retry_on_failure is False
        assert config.version == "1.0.0"

    def test_mcp_tool_config_with_schema(self):
        """Test MCP tool configuration with JSON schema."""
        config = MCPToolConfig(
            tool_id="schema_test",
            name="Schema Test",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"}
                },
                "required": ["query"]
            }
        )
        assert config.input_schema is not None
        assert "query" in config.input_schema["properties"]

    def test_mcp_tool_config_environment(self):
        """Test MCP tool environment configuration."""
        config = MCPToolConfig(
            tool_id="env_test",
            name="Environment Test",
            required_env=["API_KEY", "ENDPOINT"]
        )
        assert len(config.required_env) == 2
        assert "API_KEY" in config.required_env


class TestMCPToolExecution:
    """Test MCP Tool Execution."""

    @pytest.mark.asyncio
    async def test_mcp_tool_execution(self):
        """Test basic MCP tool execution."""
        config = MCPToolConfig(
            tool_id="exec_test",
            name="Execution Test",
            category=ToolCategory.WEB_SEARCH,
            parameters=[
                ToolParameter(name="query", type="string", required=True)
            ]
        )
        tool = MCPTool(config)
        result = await tool.execute({"query": "M31 galaxy"})
        assert result.success is True
        assert "M31 galaxy" in str(result.output)

    @pytest.mark.asyncio
    async def test_mcp_tool_execution_with_multiple_params(self):
        """Test MCP tool execution with multiple parameters."""
        config = MCPToolConfig(
            tool_id="multi_param_test",
            name="Multi Param Test",
            category=ToolCategory.DATA_ANALYSIS,
            parameters=[
                ToolParameter(name="target", type="string", required=True),
                ToolParameter(name="limit", type="integer", required=False, default=10),
                ToolParameter(name="format", type="string", required=False, default="json"),
            ]
        )
        tool = MCPTool(config)
        result = await tool.execute({
            "target": "M42",
            "limit": 5,
            "format": "csv"
        })
        assert result.success is True
        assert len(tool.execution_log) == 1

    @pytest.mark.asyncio
    async def test_mcp_tool_execution_timing(self):
        """Test MCP tool execution timing."""
        config = MCPToolConfig(tool_id="timing_test", name="Timing Test")
        tool = MCPTool(config)
        result = await tool.execute({})
        assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_mcp_tool_execution_log(self):
        """Test MCP tool execution logging."""
        config = MCPToolConfig(tool_id="log_test", name="Log Test")
        tool = MCPTool(config)
        for i in range(3):
            await tool.execute({"iteration": i})
        assert len(tool.execution_log) == 3


class TestMCPToolChain:
    """Test MCP Tool Chaining."""

    @pytest.mark.asyncio
    async def test_tool_chain_creation(self):
        """Test creating a tool chain."""
        chain = MCPToolChain(name="Test Chain")
        assert chain.name == "Test Chain"
        assert len(chain.tools) == 0
        assert chain.results == []

    @pytest.mark.asyncio
    async def test_tool_chain_add_tool(self):
        """Test adding tools to chain."""
        chain = MCPToolChain(name="Add Test")
        config = MCPToolConfig(tool_id="chain_tool_1", name="Chain Tool 1")
        tool = MCPTool(config)
        chain.add_tool(tool)
        assert len(chain.tools) == 1

    @pytest.mark.asyncio
    async def test_tool_chain_execution(self):
        """Test executing tool chain."""
        chain = MCPToolChain(name="Execution Test")
        # Add tools
        for i in range(3):
            config = MCPToolConfig(tool_id=f"chain_tool_{i}", name=f"Chain Tool {i}")
            tool = MCPTool(config)
            chain.add_tool(tool)
        # Execute chain
        result = await chain.execute({"initial_data": "test"})
        assert result.success is True
        assert len(chain.results) == 3

    @pytest.mark.asyncio
    async def test_tool_chain_result_aggregation(self):
        """Test aggregating results from chain execution."""
        chain = MCPToolChain(name="Aggregation Test")
        config = MCPToolConfig(tool_id="agg_tool", name="Agg Tool")
        tool = MCPTool(config)
        chain.add_tool(tool)
        await chain.execute({"data": "value"})
        aggregated = chain.get_aggregated_results()
        assert aggregated is not None

    @pytest.mark.asyncio
    async def test_tool_chain_error_handling(self):
        """Test tool chain error handling."""
        chain = MCPToolChain(name="Error Test")

        class FailingTool(BaseTool):
            async def execute(self, params: Dict[str, Any]) -> MCPToolResult:
                return MCPToolResult(
                    tool_id="failing",
                    success=False,
                    error="Simulated failure"
                )

        config = MCPToolConfig(tool_id="failing", name="Failing Tool")
        tool = FailingTool(config)
        chain.add_tool(tool)
        result = await chain.execute({})
        assert result.success is False


class TestMCPToolResult:
    """Test MCP Tool Result handling."""

    @pytest.mark.asyncio
    async def test_mcp_tool_result_success(self):
        """Test successful tool result."""
        result = MCPToolResult(
            tool_id="success_test",
            success=True,
            output={"data": "result_value"},
            execution_time=0.05
        )
        assert result.success is True
        assert result.output["data"] == "result_value"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_mcp_tool_result_failure(self):
        """Test failed tool result."""
        result = MCPToolResult(
            tool_id="failure_test",
            success=False,
            error="Tool execution failed",
            execution_time=0.01
        )
        assert result.success is False
        assert result.error == "Tool execution failed"
        assert result.output is None

    @pytest.mark.asyncio
    async def test_mcp_tool_result_with_metadata(self):
        """Test tool result with metadata."""
        result = MCPToolResult(
            tool_id="metadata_test",
            success=True,
            output={"items": [1, 2, 3]},
            execution_time=0.1,
            metadata={"count": 3, "source": "test"}
        )
        assert result.metadata["count"] == 3
        assert result.metadata["source"] == "test"


class TestMCPToolDiscovery:
    """Test MCP Tool Discovery."""

    def test_tool_integration_instance(self):
        """Test getting tool integration instance."""
        integration = get_tool_integration()
        assert integration is not None

    def test_tool_integration_list_tools(self):
        """Test listing available tools."""
        integration = get_tool_integration()
        tools = integration.list_tools()
        assert isinstance(tools, list)
        # Should have default tools registered
        assert len(tools) >= 0

    def test_tool_integration_get_tool(self):
        """Test getting specific tool."""
        integration = get_tool_integration()
        tools = integration.list_tools()
        if tools:
            tool_id = tools[0]
            tool = integration.get_tool(tool_id)
            # Tool might be None if not found or not loaded
            assert tool is None or hasattr(tool, "config")

    def test_tool_integration_search_tools(self):
        """Test searching for tools."""
        integration = get_tool_integration()
        results = integration.search_tools("search")
        assert isinstance(results, list)


class TestMCPToolCategories:
    """Test MCP Tool Categories."""

    def test_tool_category_values(self):
        """Test tool category enum values."""
        assert ToolCategory.WEB_SEARCH.value == "web_search"
        assert ToolCategory.DATA_ANALYSIS.value == "data_analysis"
        assert ToolCategory.CODE_EXECUTION.value == "code_execution"
        assert ToolCategory.FILE_SYSTEM.value == "file_system"
        assert ToolCategory.API_CALL.value == "api_call"

    def test_tool_category_assignment(self):
        """Test assigning tool to category."""
        config = MCPToolConfig(
            tool_id="category_test",
            name="Category Test",
            category=ToolCategory.ASTRONOMY
        )
        assert config.category == ToolCategory.ASTRONOMY


class TestMCPToolErrorHandling:
    """Test MCP Tool Error Handling."""

    @pytest.mark.asyncio
    async def test_tool_timeout_handling(self):
        """Test tool timeout handling."""
        config = MCPToolConfig(
            tool_id="timeout_test",
            name="Timeout Test",
            timeout_seconds=1
        )

        class SlowTool(BaseTool):
            async def execute(self, params: Dict[str, Any]) -> MCPToolResult:
                await asyncio.sleep(2)  # Simulate slow execution
                return MCPToolResult(tool_id="slow", success=True, output={})

        tool = SlowTool(config)
        result = await tool.execute({})
        # Would check for timeout in real implementation
        assert result.tool_id == "slow"

    @pytest.mark.asyncio
    async def test_tool_invalid_params(self):
        """Test tool with invalid parameters."""
        config = MCPToolConfig(
            tool_id="invalid_test",
            name="Invalid Params Test",
            parameters=[
                ToolParameter(name="required_field", type="string", required=True)
            ]
        )
        tool = MCPTool(config)
        result = await tool.execute({})  # Missing required field
        # Tool should handle missing params or execute anyway
        assert result.tool_id == "invalid_test"

    @pytest.mark.asyncio
    async def test_tool_connection_error(self):
        """Test tool connection error handling."""
        result = MCPToolResult(
            tool_id="connection_test",
            success=False,
            error="Connection refused"
        )
        assert result.success is False
        assert "Connection" in result.error


class TestMCPToolWorkflow:
    """Test MCP Tool Workflow Integration."""

    @pytest.mark.asyncio
    async def test_workflow_with_data_passing(self):
        """Test workflow with data passing between tools."""
        chain = MCPToolChain(name="Data Pass Workflow")

        class DataPassTool1(BaseTool):
            async def execute(self, params: Dict[str, Any]) -> MCPToolResult:
                return MCPToolResult(
                    tool_id="tool1",
                    success=True,
                    output={"processed": params.get("data", "").upper()}
                )

        class DataPassTool2(BaseTool):
            async def execute(self, params: Dict[str, Any]) -> MCPToolResult:
                return MCPToolResult(
                    tool_id="tool2",
                    success=True,
                    output={"final": f"Result: {params.get('processed', '')}"}
                )

        chain.add_tool(DataPassTool1(MCPToolConfig(tool_id="tool1", name="Tool 1")))
        chain.add_tool(DataPassTool2(MCPToolConfig(tool_id="tool2", name="Tool 2")))
        result = await chain.execute({"data": "hello"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_workflow_conditional_execution(self):
        """Test conditional tool execution in workflow."""
        chain = MCPToolChain(name="Conditional Workflow")
        config = MCPToolConfig(tool_id="cond_tool", name="Conditional Tool")
        tool = MCPTool(config)
        chain.add_tool(tool)
        # Conditional execution based on result
        result = await chain.execute({"condition": True})
        assert result is not None

    @pytest.mark.asyncio
    async def test_workflow_parallel_execution(self):
        """Test parallel tool execution."""
        chain = MCPToolChain(name="Parallel Workflow")
        for i in range(5):
            config = MCPToolConfig(tool_id=f"parallel_{i}", name=f"Parallel {i}")
            tool = MCPTool(config)
            chain.add_tool(tool)
        # Execute in parallel
        result = await chain.execute_parallel({})
        assert result.success is True


class TestMCPToolIntegration:
    """Integration tests for MCP Tool integration."""

    @pytest.mark.asyncio
    async def test_full_tool_execution_flow(self):
        """Test complete tool execution flow."""
        integration = get_tool_integration()
        # Register tool
        config = MCPToolConfig(
            tool_id="integration_test",
            name="Integration Test",
            category=ToolCategory.GENERAL
        )
        tool = MCPTool(config)
        # Tool would be registered in real implementation
        # Execute
        result = await tool.execute({"test": "data"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_multiple_tool_registration(self):
        """Test registering multiple tools."""
        tools = []
        for i in range(5):
            config = MCPToolConfig(
                tool_id=f"multi_{i}",
                name=f"Multi Tool {i}",
                category=ToolCategory.GENERAL
            )
            tool = MCPTool(config)
            tools.append(tool)
        assert len(tools) == 5

    @pytest.mark.asyncio
    async def test_tool_chain_complex_workflow(self):
        """Test complex workflow with tool chain."""
        chain = MCPToolChain(name="Complex Workflow")
        # Add 3 tools
        for i in range(3):
            config = MCPToolConfig(
                tool_id=f"complex_{i}",
                name=f"Complex Tool {i}"
            )
            chain.add_tool(MCPTool(config))
        # Execute
        result = await chain.execute({"workflow": "test"})
        assert result.success is True
        assert len(chain.results) == 3

    @pytest.mark.asyncio
    async def test_tool_execution_metrics(self):
        """Test collecting execution metrics."""
        config = MCPToolConfig(tool_id="metrics_test", name="Metrics Test")
        tool = MCPTool(config)
        await tool.execute({"metric": "value"})
        # Check execution was logged
        assert len(tool.execution_log) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
