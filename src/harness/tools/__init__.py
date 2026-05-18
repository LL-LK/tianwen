"""
TianwenAGI Harness - MCP工具集成层
集成MCP服务器、GitHub搜索、Web搜索、天文专用工具
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import asyncio
import logging

logger = logging.getLogger("harness.tools")

# MCP工具注册表
_mcp_tools: Dict[str, Callable] = {}
_active_mcp_servers: Dict[str, Any] = {}


class ToolCategory(Enum):
    """工具类别"""
    WEB_SEARCH = "web_search"           # 网页搜索
    GITHUB = "github"                   # GitHub操作
    BROWSER = "browser"                # 浏览器自动化
    ASTRONOMY_CATALOG = "astronomy_catalog"  # 天文星表
    ASTRONOMY_OBSERVATION = "astronomy_observation"  # 观测控制
    DATA_PROCESSING = "data_processing"  # 数据处理
    CODE_EXECUTION = "code_execution"   # 代码执行
    FILE_SYSTEM = "file_system"        # 文件系统
    ASTRONOMY_QUERY = "astronomy_query"  # 天文数据库查询
    TIME_DOMAIN = "time_domain"        # 时域天文
    CUSTOM = "custom"                   # 自定义


@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Any] = field(default_factory=dict)
    returns: Dict[str, Any] = field(default_factory=dict)
    requires_auth: bool = False
    rate_limit: Optional[str] = None  # e.g., "100/hour"
    cost: float = 0.0
    is_async: bool = True


class BaseTool(ABC):
    """工具基类"""

    def __init__(self, metadata: ToolMetadata):
        self.metadata = metadata

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        pass

    async def validate_params(self, params: Dict) -> bool:
        """验证参数"""
        required = [p for p, v in self.metadata.parameters.items() if v.get("required", False)]
        return all(p in params for p in required)


class MCPToolIntegration:
    """
    MCP工具集成管理器
    负责MCP工具的注册、调度、结果聚合
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_registry: Dict[str, Callable] = {}

    def register_tool(self, name: str, tool: BaseTool):
        """注册工具"""
        self._tools[name] = tool
        self._tool_registry[name] = tool.execute
        logger.info(f"Registered MCP tool: {name}")

    def register_function(self, name: str, func: Callable):
        """注册函数"""
        self._tool_registry[name] = func
        logger.info(f"Registered function tool: {name}")

    async def execute_tool(self, name: str, **kwargs) -> Any:
        """执行工具"""
        if name not in self._tool_registry:
            raise ValueError(f"Tool '{name}' not found")

        func = self._tool_registry[name]
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(**kwargs)
            else:
                return func(**kwargs)
        except Exception as e:
            logger.error(f"Tool '{name}' execution failed: {e}")
            raise

    async def batch_execute(
        self,
        calls: List[Dict[str, Any]]
    ) -> List[Any]:
        """批量执行工具调用"""
        tasks = [self.execute_tool(call["name"], **call.get("params", {})) for call in calls]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def list_tools(self) -> List[str]:
        return list(self._tool_registry.keys())

    def get_tools_by_category(self, category: ToolCategory) -> List[str]:
        return [name for name, tool in self._tools.items()
                if tool.metadata.category == category]


class WebSearchTool(BaseTool):
    """网页搜索工具"""

    def __init__(self):
        super().__init__(ToolMetadata(
            name="web_search",
            description="Search the web for information",
            category=ToolCategory.WEB_SEARCH,
            parameters={
                "query": {"type": "string", "required": True},
                "limit": {"type": "integer", "default": 5},
                "source": {"type": "string", "default": "auto"}
            }
        ))
        self._search_func = None

    def set_search_func(self, func: Callable):
        """设置搜索函数"""
        self._search_func = func

    async def execute(self, query: str, limit: int = 5, **kwargs) -> List[Dict]:
        if self._search_func:
            return await self._search_func(query, limit)
        return []


class GitHubSearchTool(BaseTool):
    """GitHub搜索工具"""

    def __init__(self):
        super().__init__(ToolMetadata(
            name="github_search",
            description="Search GitHub repositories and code",
            category=ToolCategory.GITHUB,
            parameters={
                "query": {"type": "string", "required": True},
                "search_type": {"type": "string", "default": "repositories"},
                "limit": {"type": "integer", "default": 10}
            }
        ))
        self._search_func = None

    def set_search_func(self, func: Callable):
        self._search_func = func

    async def execute(self, query: str, search_type: str = "repositories", **kwargs) -> List[Dict]:
        if self._search_func:
            return await self._search_func(query, search_type)
        return []


class AstronomyCatalogTool(BaseTool):
    """天文星表查询工具"""

    def __init__(self):
        super().__init__(ToolMetadata(
            name="astronomy_catalog",
            description="Query astronomical catalogs (SIMBAD, NED, VizieR)",
            category=ToolCategory.ASTRONOMY_CATALOG,
            parameters={
                "catalog": {"type": "string", "required": True},  # simbad, ned, vizier
                "target": {"type": "string", "required": True},
                "params": {"type": "object", "default": {}}
            }
        ))

    async def execute(self, catalog: str, target: str, **kwargs) -> Dict:
        """执行星表查询"""
        if catalog.lower() == "simbad":
            return await self._query_simbad(target, **kwargs)
        elif catalog.lower() == "ned":
            return await self._query_ned(target, **kwargs)
        elif catalog.lower() == "vizier":
            return await self._query_vizier(target, **kwargs)
        return {"error": f"Unknown catalog: {catalog}"}

    async def _query_simbad(self, target: str, **kwargs) -> Dict:
        # SIMBAD查询实现
        return {"target": target, "catalog": "SIMBAD", "data": {}}

    async def _query_ned(self, target: str, **kwargs) -> Dict:
        return {"target": target, "catalog": "NED", "data": {}}

    async def _query_vizier(self, target: str, **kwargs) -> Dict:
        return {"target": target, "catalog": "VizieR", "data": {}}


class FileSystemTool(BaseTool):
    """文件系统工具"""

    def __init__(self):
        super().__init__(ToolMetadata(
            name="file_system",
            description="Read, write, and manage files",
            category=ToolCategory.FILE_SYSTEM,
            parameters={
                "operation": {"type": "string", "required": True},  # read, write, list, search
                "path": {"type": "string", "required": True},
                "content": {"type": "string", "default": None}
            }
        ))

    async def execute(self, operation: str, path: str, **kwargs) -> Any:
        """执行文件系统操作"""
        if operation == "read":
            return await self._read_file(path)
        elif operation == "write":
            return await self._write_file(path, kwargs.get("content", ""))
        elif operation == "list":
            return await self._list_dir(path)
        elif operation == "search":
            return await self._search_files(path, kwargs.get("pattern", "*"))
        return {"error": f"Unknown operation: {operation}"}

    async def _read_file(self, path: str) -> Dict:
        try:
            with open(path, 'r') as f:
                content = f.read()
            return {"path": path, "content": content, "size": len(content)}
        except Exception as e:
            return {"error": str(e)}

    async def _write_file(self, path: str, content: str) -> Dict:
        try:
            with open(path, 'w') as f:
                f.write(content)
            return {"path": path, "written": len(content)}
        except Exception as e:
            return {"error": str(e)}

    async def _list_dir(self, path: str) -> List[str]:
        import os
        try:
            return os.listdir(path)
        except Exception:
            return []

    async def _search_files(self, path: str, pattern: str) -> List[str]:
        import glob
        return glob.glob(f"{path}/{pattern}")


# 默认工具实例
default_tools = {
    "web_search": WebSearchTool(),
    "github_search": GitHubSearchTool(),
    "astronomy_catalog": AstronomyCatalogTool(),
    "file_system": FileSystemTool(),
}


def get_tool_integration() -> MCPToolIntegration:
    """获取工具集成实例"""
    integration = MCPToolIntegration()
    for name, tool in default_tools.items():
        integration.register_tool(name, tool)
    return integration


# Import astronomy tools
from harness.tools.astronomy import (
    SIMBADTool,
    VizieRTool,
    AstroplanTool,
    get_astronomy_tools,
    execute_astronomy_tool,
)

__all__ = [
    # Base classes
    "ToolCategory",
    "ToolMetadata",
    "BaseTool",
    "MCPToolIntegration",
    # Default tools
    "WebSearchTool",
    "GitHubSearchTool",
    "AstronomyCatalogTool",
    "FileSystemTool",
    "default_tools",
    "get_tool_integration",
    # Astronomy tools
    "SIMBADTool",
    "VizieRTool",
    "AstroplanTool",
    "get_astronomy_tools",
    "execute_astronomy_tool",
]
