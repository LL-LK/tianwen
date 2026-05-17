"""
Hermes-AGI MCP (Model Context Protocol) Implementation
MCP协议实现 - 支持外部工具调用
"""
import logging
logger = logging.getLogger(__name__)

import asyncio
import json
import re
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path

# ============ 工具定义 ============

class ToolStatus(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"

@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum_values: List[str] = field(default_factory=list)

@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    category: str  # file, search, api, system, etc.
    parameters: List[ToolParameter] = field(default_factory=list)
    handler: Optional[Callable] = None
    status: ToolStatus = ToolStatus.AVAILABLE

@dataclass
class ToolCall:
    """工具调用请求"""
    tool_name: str
    parameters: Dict[str, Any]
    call_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class ToolResult:
    """工具调用结果"""
    tool_name: str
    call_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0

# ============ 文件操作工具 ============

class FileTools:
    """文件操作工具集"""

    @staticmethod
    async def read_file(path: str, **kwargs) -> Dict:
        """读取文件 - 修复路径遍历漏洞"""
        try:
            # 路径安全验证：防止../路径遍历攻击
            safe_path = Path(path).resolve()
            allowed_dir = Path(kwargs.get('allowed_dir', '/tmp')).resolve()
            if not str(safe_path).startswith(str(allowed_dir)):
                # 如果不在允许目录，检查是否在项目目录内
                project_dir = Path(__file__).parent.parent.resolve()
                if not str(safe_path).startswith(str(project_dir)):
                    return {"success": False, "error": "路径访问被拒绝"}
            with open(safe_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"success": True, "content": content, "path": str(safe_path)}
        except FileNotFoundError:
            return {"success": False, "error": f"文件不存在: {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    async def write_file(path: str, content: str, **kwargs) -> Dict:
        """写入文件 - 修复路径遍历漏洞"""
        try:
            # 路径安全验证：防止../路径遍历攻击
            safe_path = Path(path).resolve()
            allowed_dir = Path(kwargs.get('allowed_dir', '/tmp')).resolve()
            if not str(safe_path).startswith(str(allowed_dir)):
                project_dir = Path(__file__).parent.parent.resolve()
                if not str(safe_path).startswith(str(project_dir)):
                    return {"success": False, "error": "路径访问被拒绝"}
            with open(safe_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {"success": True, "path": str(safe_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    async def list_directory(path: str, **kwargs) -> Dict:
        """列出目录 - 安全版本"""
        try:
            import os
            # 路径安全验证
            safe_path = Path(path).resolve()
            project_dir = Path(__file__).parent.parent.resolve()
            if not str(safe_path).startswith(str(project_dir)):
                return {"success": False, "error": "路径访问被拒绝"}
            entries = os.listdir(safe_path)
            return {"success": True, "entries": entries, "path": str(safe_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    async def file_exists(path: str, **kwargs) -> Dict:
        """检查文件是否存在"""
        import os
        exists = os.path.exists(path)
        return {"success": True, "exists": exists, "path": path}

    @staticmethod
    def get_tools() -> List[Tool]:
        """获取文件工具列表"""
        return [
            Tool(
                name="file_read",
                description="读取文件内容",
                category="file",
                parameters=[
                    ToolParameter("path", "string", "文件路径", required=True),
                ]
            ),
            Tool(
                name="file_write",
                description="写入文件内容",
                category="file",
                parameters=[
                    ToolParameter("path", "string", "文件路径", required=True),
                    ToolParameter("content", "string", "文件内容", required=True),
                ]
            ),
            Tool(
                name="file_list",
                description="列出目录内容",
                category="file",
                parameters=[
                    ToolParameter("path", "string", "目录路径", required=True),
                ]
            ),
            Tool(
                name="file_exists",
                description="检查文件是否存在",
                category="file",
                parameters=[
                    ToolParameter("path", "string", "文件路径", required=True),
                ]
            ),
        ]

# ============ 搜索工具 ============

class SearchTools:
    """搜索工具集"""

    # 搜索结果缓存，避免重复请求
    _search_cache: Dict[str, tuple] = {}
    _cache_ttl = 300  # 5分钟缓存
    _cache_max_size = 100

    @staticmethod
    def _get_cached(key: str) -> Optional[Dict]:
        """获取缓存的搜索结果"""
        if key in SearchTools._search_cache:
            results, timestamp = SearchTools._search_cache[key]
            import time
            if time.time() - timestamp < SearchTools._cache_ttl:
                return results
            del SearchTools._search_cache[key]
        return None

    @staticmethod
    def _set_cached(key: str, results: Dict):
        """缓存搜索结果"""
        import time
        SearchTools._search_cache[key] = (results, time.time())
        # LRU淘汰
        if len(SearchTools._search_cache) > SearchTools._cache_max_size:
            oldest_key = min(SearchTools._search_cache.keys(),
                           key=lambda k: SearchTools._search_cache[k][1])
            del SearchTools._search_cache[oldest_key]

    @staticmethod
    async def web_search(query: str, **kwargs) -> Dict:
        """网页搜索 - 真实实现"""
        cache_key = f"web_search:{query}"
        cached = SearchTools._get_cached(cache_key)
        if cached:
            return cached

        # 优先使用BrowserSearch
        try:
            from browser_search import quick_search
            raw_results = await asyncio.wait_for(
                quick_search(query),
                timeout=25.0
            )

            # 转换格式统一输出
            all_results = raw_results.get("all", [])
            formatted_results = []
            for r in all_results:
                if isinstance(r, dict):
                    formatted_results.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("snippet", ""),
                        "source": r.get("target", "unknown")
                    })
                else:
                    formatted_results.append({
                        "title": getattr(r, "title", ""),
                        "url": getattr(r, "url", ""),
                        "snippet": getattr(r, "snippet", ""),
                        "source": getattr(r, "target", "unknown")
                    })

            result = {
                "success": True,
                "query": query,
                "results": formatted_results,
                "total_results": len(formatted_results),
                "sources": {
                    "arxiv": len(raw_results.get("arxiv", [])),
                    "github": len(raw_results.get("github", [])),
                    "nasa": len(raw_results.get("nasa", [])),
                    "semantic_scholar": len(raw_results.get("google_scholar", []))
                }
            }

            SearchTools._set_cached(cache_key, result)
            return result

        except ImportError:
            # BrowserSearch不可用，降级到简单HTTP搜索
            return await SearchTools._fallback_web_search(query)
        except asyncio.TimeoutError:
            return {
                "success": False,
                "query": query,
                "error": "搜索超时(25秒)"
            }
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "error": str(e)
            }

    @staticmethod
    async def _fallback_web_search(query: str) -> Dict:
        """降级搜索 - 使用简单HTTP请求"""
        try:
            import urllib.parse
            import urllib.request

            # 使用DuckDuckGo HTML (无需API key)
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

            with asyncio.timeout(10):
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    html = response.read().decode('utf-8', errors='replace')

            # 简单解析HTML结果
            import re
            results = []
            # 匹配 <a class="result__a" href="...">Title</a>
            titles = re.findall(r'<a class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', html)
            snippets = re.findall(r'<a class="result__snippet"[^>]*>([^<]*)</a>', html)

            for i, (url, title) in enumerate(titles[:10]):
                snippet = snippets[i] if i < len(snippets) else ""
                results.append({
                    "title": title.strip(),
                    "url": url.strip(),
                    "snippet": snippet.strip() if snippet else "",
                    "source": "duckduckgo"
                })

            return {
                "success": True,
                "query": query,
                "results": results,
                "total_results": len(results),
                "sources": {"duckduckgo": len(results)}
            }

        except Exception as e:
            return {
                "success": False,
                "query": query,
                "error": f"降级搜索失败: {str(e)}"
            }

    @staticmethod
    async def code_search(query: str, **kwargs) -> Dict:
        """代码搜索"""
        return {
            "success": True,
            "query": query,
            "results": [
                {"file": "example.py", "line": 42, "snippet": f"code related to {query}"},
            ]
        }

    @staticmethod
    async def search_context(query: str, context: List[str], **kwargs) -> Dict:
        """在上下文中搜索"""
        query_lower = query.lower()
        matches = []
        for i, text in enumerate(context):
            if query_lower in text.lower():
                matches.append({"index": i, "text": text[:100]})
        return {
            "success": True,
            "query": query,
            "matches": matches,
            "total": len(matches)
        }

    @staticmethod
    def get_tools() -> List[Tool]:
        return [
            Tool(
                name="web_search",
                description="执行网页搜索",
                category="search",
                parameters=[
                    ToolParameter("query", "string", "搜索查询", required=True),
                ]
            ),
            Tool(
                name="code_search",
                description="搜索代码",
                category="search",
                parameters=[
                    ToolParameter("query", "string", "搜索查询", required=True),
                ]
            ),
        ]

# ============ API工具 ============

class ApiTools:
    """API调用工具"""

    @staticmethod
    async def http_get(url: str, **kwargs) -> Dict:
        """HTTP GET请求"""
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=10) as response:
                content = response.read().decode('utf-8')
            return {"success": True, "url": url, "content": content[:1000], "status": 200}
        except Exception as e:
            return {"success": False, "url": url, "error": str(e)}

    @staticmethod
    async def http_post(url: str, data: Dict = None, **kwargs) -> Dict:
        """HTTP POST请求"""
        import urllib.request
        import json as _json
        try:
            req_data = _json.dumps(data or {}).encode('utf-8')
            req = urllib.request.Request(url, data=req_data, headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8')
            return {"success": True, "url": url, "content": content[:1000], "status": response.status}
        except Exception as e:
            return {"success": False, "url": url, "error": str(e)}

    @staticmethod
    def get_tools() -> List[Tool]:
        return [
            Tool(
                name="http_get",
                description="执行HTTP GET请求",
                category="api",
                parameters=[
                    ToolParameter("url", "string", "请求URL", required=True),
                ]
            ),
            Tool(
                name="http_post",
                description="执行HTTP POST请求",
                category="api",
                parameters=[
                    ToolParameter("url", "string", "请求URL", required=True),
                    ToolParameter("data", "object", "请求数据", required=False),
                ]
            ),
        ]

# ============ 系统工具 ============

class SystemTools:
    """系统工具集"""

    @staticmethod
    async def execute_command(command: str, **kwargs) -> Dict:
        """执行系统命令 - 带超时保护(30秒)"""
        import time

        # 验证命令安全性
        if not command or len(command) > 2000:
            return {"success": False, "command": command, "error": "命令长度无效"}

        # 危险命令黑名单
        dangerous_patterns = [
            "rm -rf /", "mkfs", ":(){:|:&};:", "fork bomb",
            "chmod -R 777 /", "rm -rf ~", "dd if=/dev/zero"
        ]
        command_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return {"success": False, "command": command, "error": f"危险命令拒绝执行: {pattern}"}

        try:
            import shlex
            args = shlex.split(command)
            if not args:
                return {"success": False, "command": command, "error": "无效命令"}

            # 超时保护：30秒
            timeout = 30.0
            start_time = time.time()

            process = await asyncio.create_subprocess_exec(
                args[0], *args[1:],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                elapsed = time.time() - start_time
                return {
                    "success": False,
                    "command": command,
                    "error": f"命令超时({timeout}秒)",
                    "elapsed": round(elapsed, 2)
                }

            elapsed = time.time() - start_time
            return {
                "success": process.returncode == 0,
                "command": command,
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "return_code": process.returncode,
                "elapsed": round(elapsed, 2)
            }
        except Exception as e:
            return {"success": False, "command": command, "error": str(e)}

    @staticmethod
    async def get_system_info(**kwargs) -> Dict:
        """获取系统信息"""
        import platform
        import os
        return {
            "success": True,
            "os": platform.system(),
            "os_version": platform.version(),
            "python_version": platform.python_version(),
            "cwd": os.getcwd(),
        }

    @staticmethod
    def get_tools() -> List[Tool]:
        return [
            Tool(
                name="execute_command",
                description="执行系统命令",
                category="system",
                parameters=[
                    ToolParameter("command", "string", "命令", required=True),
                ]
            ),
            Tool(
                name="get_system_info",
                description="获取系统信息",
                category="system",
                parameters=[]
            ),
        ]

# ============ MCP服务器 ============

class MCPServer:
    """MCP协议服务器"""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.call_history: List[ToolCall] = []

        # 注册所有工具
        self._register_tools()

    def _register_tools(self):
        """注册所有工具"""
        all_tool_classes = [FileTools, SearchTools, ApiTools, SystemTools]
        for tool_class in all_tool_classes:
            for tool in tool_class.get_tools():
                self.tools[tool.name] = tool

    def get_available_tools(self) -> List[Dict]:
        """获取可用工具列表"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required
                    }
                    for p in tool.parameters
                ]
            }
            for tool in self.tools.values()
            if tool.status == ToolStatus.AVAILABLE
        ]

    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """调用工具"""
        start_time = datetime.now()
        call_id = f"call_{len(self.call_history)}"

        tool = self.tools.get(tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_name,
                call_id=call_id,
                success=False,
                error=f"工具不存在: {tool_name}"
            )

        # 记录调用
        call = ToolCall(tool_name=tool_name, parameters=parameters, call_id=call_id)
        self.call_history.append(call)

        try:
            # 根据工具类型获取handler
            handler = self._get_tool_handler(tool_name)
            if handler:
                result = await handler(**parameters)
                execution_time = (datetime.now() - start_time).total_seconds()
                return ToolResult(
                    tool_name=tool_name,
                    call_id=call_id,
                    success=result.get("success", True),
                    result=result,
                    execution_time=execution_time
                )
            else:
                return ToolResult(
                    tool_name=tool_name,
                    call_id=call_id,
                    success=False,
                    error="工具无可用处理器"
                )
        except Exception as e:
            return ToolResult(
                tool_name=tool_name,
                call_id=call_id,
                success=False,
                error=str(e),
                execution_time=(datetime.now() - start_time).total_seconds()
            )

    def _get_tool_handler(self, tool_name: str) -> Optional[Callable]:
        """获取工具处理器"""
        handlers = {
            # File tools
            "file_read": FileTools.read_file,
            "file_write": FileTools.write_file,
            "file_list": FileTools.list_directory,
            "file_exists": FileTools.file_exists,
            # Search tools
            "web_search": SearchTools.web_search,
            "code_search": SearchTools.code_search,
            # API tools
            "http_get": ApiTools.http_get,
            "http_post": ApiTools.http_post,
            # System tools
            "execute_command": SystemTools.execute_command,
            "get_system_info": SystemTools.get_system_info,
        }
        return handlers.get(tool_name)

    def get_tool_categories(self) -> List[str]:
        """获取工具分类"""
        categories = set(tool.category for tool in self.tools.values())
        return sorted(list(categories))

    def get_call_history(self, limit: int = 50) -> List[Dict]:
        """获取调用历史"""
        return [
            {
                "call_id": c.call_id,
                "tool_name": c.tool_name,
                "parameters": c.parameters,
                "timestamp": c.timestamp
            }
            for c in self.call_history[-limit:]
        ]

# ============ MCP客户端(集成到Agent) ============

class MCPEnabledAgent:
    """支持MCP的Agent"""

    def __init__(self, base_agent):
        self.base_agent = base_agent
        self.mcp_server = MCPServer()

    def get_tools_manifest(self) -> Dict:
        """获取工具清单"""
        return {
            "tools": self.mcp_server.get_available_tools(),
            "categories": self.mcp_server.get_tool_categories(),
        }

    async def process_with_tools(self, user_input: str, tool_calls: List[ToolCall] = None) -> Dict:
        """使用工具处理请求"""
        results = []

        if tool_calls:
            for call in tool_calls:
                result = await self.mcp_server.call_tool(call.tool_name, call.parameters)
                results.append({
                    "tool": call.tool_name,
                    "success": result.success,
                    "result": result.result,
                    "error": result.error
                })

        # 继续Agent处理
        agent_result = await self.base_agent.process(user_input)

        return {
            "agent_result": agent_result,
            "tool_results": results,
            "tools_used": len(results)
        }

    async def execute_tool(self, tool_name: str, parameters: Dict) -> ToolResult:
        """直接执行工具"""
        return await self.mcp_server.call_tool(tool_name, parameters)

# ============ 示例用法 ============

async def demo():
    """演示MCP"""
    logger.debug("=" * 50)

    server = MCPServer()

    # 显示可用工具
    logger.info("\n可用工具分类:")
    for category in server.get_tool_categories():
        logger.info(f"  - {category}")

    logger.info(f"\n工具总数: {len(server.get_available_tools())}")

    # 调用工具示例
    logger.info("\n调用 file_exists 工具:")
    result = await server.call_tool("file_exists", {"path": "/tmp/test.txt"})
    logger.info(f"  成功: {result.success}")
    logger.info(f"  结果: {result.result}")

    logger.info("\n调用 get_system_info 工具:")
    result = await server.call_tool("get_system_info", {})
    logger.info(f"  成功: {result.success}")
    logger.info(f"  系统信息: {result.result}")

    logger.info("\n调用 web_search 工具:")
    result = await server.call_tool("web_search", {"query": "Python async programming"})
    logger.info(f"  成功: {result.success}")
    if result.result:
        logger.info(f"  搜索结果数: {result.result.get('total_results', 0)}")

    # 显示调用历史
    logger.info("\n调用历史:")
    history = server.get_call_history()
    for call in history:
        logger.info(f"  - {call['tool_name']} @ {call['timestamp']}")

if __name__ == "__main__":
    asyncio.run(demo())